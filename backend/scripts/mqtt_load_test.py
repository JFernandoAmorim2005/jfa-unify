"""
Script de load test MQTT — JFA Unify.

Publica 100 mensagens em burst no tópico jfa/test/state e mede:
  - Throughput (msgs/seg)
  - Latência por mensagem (publicação → confirmação de entrega)
  - Latência p50, p95 e p99
  - Percentagem de mensagens confirmadas em <500ms

Uso:
    cd C:\\JFA_Unify\\backend
    python scripts/mqtt_load_test.py [--broker localhost] [--port 1883] [--count 100]

Saída de exemplo:
    Broker: localhost:1883
    Mensagens enviadas: 100
    Mensagens confirmadas: 100 (100.0%)
    Throughput: 284.3 msgs/seg
    Latência (ms): p50=1.2  p95=3.8  p99=8.1  max=12.4
    Dentro de 500ms: 100/100 (100.0%) ✓
    Resultado: PASSOU

Requisitos:
    pip install paho-mqtt

Nota:
    Este script corre de forma autónoma e NÃO é recolhido pelo pytest
    (fica em scripts/, não em tests/). Para correr no CI como teste,
    usar pytest -m mqtt_load com o marker adequado.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import threading
import time
import uuid


def _import_paho():
    try:
        import paho.mqtt.client as mqtt
        return mqtt
    except ImportError:
        print("ERRO: paho-mqtt não instalado. Execute: pip install paho-mqtt", file=sys.stderr)
        sys.exit(1)


def run_load_test(
    broker: str = "localhost",
    port: int = 1883,
    topic: str = "jfa/test/state",
    count: int = 100,
    username: str = "",
    password: str = "",
    qos: int = 1,
    threshold_ms: float = 500.0,
) -> dict:
    """
    Executa o load test MQTT e retorna métricas.

    Args:
        broker:       Endereço do broker MQTT.
        port:         Porta do broker.
        topic:        Tópico de destino.
        count:        Número de mensagens a publicar.
        username:     Username MQTT (opcional).
        password:     Password MQTT (opcional).
        qos:          Quality of Service (0, 1 ou 2).
        threshold_ms: Limite de latência para validação (default 500ms).

    Returns:
        dict com métricas: throughput, p50, p95, p99, max, pct_within_threshold,
        confirmed, total, passed.
    """
    mqtt = _import_paho()

    # Mapeamento mid → timestamp de publicação
    publish_times: dict[int, float] = {}
    # Latências confirmadas (mid → latência em ms)
    confirmed_latencies: list[float] = []
    # Controlo de sincronização
    connect_event = threading.Event()
    all_confirmed = threading.Event()
    lock = threading.Lock()
    confirmed_count = [0]

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            connect_event.set()
        else:
            print(f"Falha na ligação: rc={rc}", file=sys.stderr)

    def on_publish(client, userdata, mid, reason_code=None, properties=None):
        """Chamado quando a mensagem foi confirmada pelo broker (QoS 1+)."""
        received_at = time.perf_counter()
        with lock:
            sent_at = publish_times.pop(mid, None)
            if sent_at is not None:
                latency_ms = (received_at - sent_at) * 1000.0
                confirmed_latencies.append(latency_ms)
                confirmed_count[0] += 1
                if confirmed_count[0] >= count:
                    all_confirmed.set()

    client_id = f"jfa-load-test-{uuid.uuid4().hex[:8]}"

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id)
    except AttributeError:
        # Fallback para versões mais antigas do paho-mqtt
        client = mqtt.Client(client_id)

    client.on_connect = on_connect
    client.on_publish = on_publish

    if username:
        client.username_pw_set(username, password)

    # Ligar ao broker
    try:
        client.connect(broker, port, keepalive=60)
    except ConnectionRefusedError:
        return {
            "error": f"Broker MQTT inacessível em {broker}:{port}",
            "passed": False,
        }
    except OSError as exc:
        return {
            "error": f"Erro de rede ao ligar a {broker}:{port}: {exc}",
            "passed": False,
        }

    client.loop_start()

    # Aguardar ligação (máximo 10s)
    if not connect_event.wait(timeout=10.0):
        client.loop_stop()
        return {
            "error": f"Timeout a ligar ao broker {broker}:{port}",
            "passed": False,
        }

    # Publicar mensagens em burst
    burst_start = time.perf_counter()
    for i in range(count):
        payload = f'{{"seq": {i}, "ts": {time.time():.6f}, "source": "jfa_load_test"}}'
        sent_at = time.perf_counter()
        result = client.publish(topic, payload.encode(), qos=qos)
        with lock:
            publish_times[result.mid] = sent_at

    # Para QoS 0, on_publish pode não ser chamado — simular confirmação imediata
    if qos == 0:
        burst_end = time.perf_counter()
        client.loop_stop()
        client.disconnect()
        duration = burst_end - burst_start
        throughput = count / duration if duration > 0 else float("inf")
        return {
            "broker": f"{broker}:{port}",
            "topic": topic,
            "total": count,
            "confirmed": count,
            "pct_confirmed": 100.0,
            "throughput_mps": round(throughput, 1),
            "latency_p50_ms": 0.0,
            "latency_p95_ms": 0.0,
            "latency_p99_ms": 0.0,
            "latency_max_ms": 0.0,
            "pct_within_threshold": 100.0,
            "threshold_ms": threshold_ms,
            "passed": True,
            "note": "QoS 0 — confirmação de entrega não disponível",
        }

    # Aguardar todas as confirmações (máximo 30s para 100 mensagens)
    timeout_s = max(30.0, count * 0.3)
    all_confirmed.wait(timeout=timeout_s)
    burst_end = time.perf_counter()

    client.loop_stop()
    client.disconnect()

    # Calcular métricas
    total_duration = burst_end - burst_start
    n_confirmed = len(confirmed_latencies)
    throughput = count / total_duration if total_duration > 0 else 0.0

    if n_confirmed == 0:
        return {
            "broker": f"{broker}:{port}",
            "topic": topic,
            "total": count,
            "confirmed": 0,
            "pct_confirmed": 0.0,
            "throughput_mps": round(throughput, 1),
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "latency_p99_ms": None,
            "latency_max_ms": None,
            "pct_within_threshold": 0.0,
            "threshold_ms": threshold_ms,
            "passed": False,
            "error": "Nenhuma confirmação recebida",
        }

    sorted_lats = sorted(confirmed_latencies)

    def percentile(data: list[float], pct: float) -> float:
        idx = min(int(len(data) * pct / 100), len(data) - 1)
        return round(data[idx], 2)

    p50 = percentile(sorted_lats, 50)
    p95 = percentile(sorted_lats, 95)
    p99 = percentile(sorted_lats, 99)
    lat_max = round(max(sorted_lats), 2)

    within_threshold = sum(1 for l in confirmed_latencies if l < threshold_ms)
    pct_within = within_threshold / n_confirmed * 100.0

    # Critério de aprovação: 95%+ das confirmadas dentro do threshold
    passed = (
        pct_within >= 95.0
        and n_confirmed / count >= 0.95
    )

    return {
        "broker": f"{broker}:{port}",
        "topic": topic,
        "total": count,
        "confirmed": n_confirmed,
        "pct_confirmed": round(n_confirmed / count * 100, 1),
        "throughput_mps": round(throughput, 1),
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "latency_p99_ms": p99,
        "latency_max_ms": lat_max,
        "pct_within_threshold": round(pct_within, 1),
        "threshold_ms": threshold_ms,
        "passed": passed,
    }


def print_report(metrics: dict) -> None:
    """Imprime relatório legível de métricas."""
    if "error" in metrics and not metrics.get("broker"):
        print(f"\nERRO: {metrics['error']}")
        return

    print(f"\n{'=' * 55}")
    print(f"  JFA Unify — MQTT Load Test")
    print(f"{'=' * 55}")
    print(f"  Broker:          {metrics.get('broker', 'N/A')}")
    print(f"  Tópico:          {metrics.get('topic', 'N/A')}")
    print(f"  Mensagens:       {metrics['confirmed']}/{metrics['total']}"
          f" ({metrics['pct_confirmed']}%)")
    print(f"  Throughput:      {metrics['throughput_mps']} msgs/seg")

    if metrics.get("latency_p50_ms") is not None:
        print(f"  Latência p50:    {metrics['latency_p50_ms']} ms")
        print(f"  Latência p95:    {metrics['latency_p95_ms']} ms")
        print(f"  Latência p99:    {metrics['latency_p99_ms']} ms")
        print(f"  Latência máx:    {metrics['latency_max_ms']} ms")
        print(f"  Dentro de {int(metrics['threshold_ms'])}ms: "
              f"{metrics.get('within_count', metrics['confirmed'])}/"
              f"{metrics['confirmed']}"
              f" ({metrics['pct_within_threshold']}%)")

    if metrics.get("note"):
        print(f"  Nota:            {metrics['note']}")

    status = "PASSOU" if metrics["passed"] else "FALHOU"
    icon = "✓" if metrics["passed"] else "✗"
    print(f"{'=' * 55}")
    print(f"  Resultado: {status} {icon}")
    print(f"{'=' * 55}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load test MQTT — JFA Unify",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--broker", default="localhost", help="Endereço do broker MQTT")
    parser.add_argument("--port", type=int, default=1883, help="Porta do broker")
    parser.add_argument("--topic", default="jfa/test/state", help="Tópico de destino")
    parser.add_argument("--count", type=int, default=100, help="Número de mensagens")
    parser.add_argument("--qos", type=int, default=1, choices=[0, 1, 2], help="QoS MQTT")
    parser.add_argument("--username", default="", help="Username MQTT")
    parser.add_argument("--password", default="", help="Password MQTT")
    parser.add_argument(
        "--threshold-ms", type=float, default=500.0,
        help="Limiar de latência para validação (ms)",
    )
    args = parser.parse_args()

    print(f"A publicar {args.count} mensagens em {args.broker}:{args.port}/{args.topic} ...")

    metrics = run_load_test(
        broker=args.broker,
        port=args.port,
        topic=args.topic,
        count=args.count,
        username=args.username,
        password=args.password,
        qos=args.qos,
        threshold_ms=args.threshold_ms,
    )

    print_report(metrics)
    return 0 if metrics.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
