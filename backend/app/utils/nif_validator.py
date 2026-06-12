"""
NIF/NIPC Validator — Portuguese Tax Number Validation & Lookup
Implements official checksum algorithm (modulo 11) and entity type classification
"""

from enum import Enum
from typing import Optional, Tuple
import requests


class EntityType(str, Enum):
    """Classificação de entidade por primeiro dígito do NIF"""
    PERSON_SINGULAR_1 = "1"  # Pessoa singular (1)
    PERSON_SINGULAR_2 = "2"  # Pessoa singular (2)
    PERSON_SINGULAR_3 = "3"  # Pessoa singular (3)
    LEGAL_ENTITY = "5"       # Pessoa coletiva / NIPC
    PUBLIC_ENTITY = "6"      # Entidade pública
    OTHER = "other"


class NIFValidationResult:
    """Resultado da validação de NIF"""

    def __init__(
        self,
        nif: str,
        is_valid: bool,
        checksum_valid: bool,
        entity_type: EntityType,
        error_message: Optional[str] = None,
        is_client: Optional[bool] = None,
        client_data: Optional[dict] = None,
        vies_data: Optional[dict] = None,
    ):
        self.nif = nif
        self.is_valid = is_valid
        self.checksum_valid = checksum_valid
        self.entity_type = entity_type
        self.error_message = error_message
        self.is_client = is_client
        self.client_data = client_data or {}
        self.vies_data = vies_data or {}

    def __str__(self) -> str:
        """Pretty print resultado"""
        lines = [
            f"{'='*60}",
            f"NIF Validation Result: {self.nif}",
            f"{'='*60}",
            f"✓ Checksum Valid: {self.checksum_valid}",
            f"✓ Overall Valid: {self.is_valid}",
            f"✓ Entity Type: {self.entity_type.value} ({self._entity_type_name()})",
        ]

        if self.error_message:
            lines.append(f"✗ Error: {self.error_message}")

        if self.is_client is not None:
            status = "✓ YES" if self.is_client else "✗ NO"
            lines.append(f"✓ Is Client in DB: {status}")
            if self.client_data:
                lines.append("  Client Data:")
                for key, value in self.client_data.items():
                    lines.append(f"    - {key}: {value}")

        if self.vies_data:
            lines.append("✓ VIES Data (EU):")
            for key, value in self.vies_data.items():
                lines.append(f"    - {key}: {value}")

        lines.append(f"{'='*60}")
        return "\n".join(lines)

    def _entity_type_name(self) -> str:
        """Descrição legível do tipo de entidade"""
        names = {
            "1": "Pessoa Singular",
            "2": "Pessoa Singular",
            "3": "Pessoa Singular",
            "5": "Pessoa Coletiva / NIPC",
            "6": "Entidade Pública",
            "other": "Outro",
        }
        return names.get(self.entity_type.value, "Desconhecido")


def validate_nif(nif: str) -> Tuple[bool, str]:
    """
    Valida NIF português usando checksum módulo 11 oficial.

    Args:
        nif: String de 9 dígitos

    Returns:
        (is_valid, error_message)
    """
    # Limpeza
    nif_clean = nif.strip().replace(" ", "").replace("-", "")

    # Validação básica
    if not nif_clean.isdigit():
        return False, "NIF deve conter apenas dígitos"

    if len(nif_clean) != 9:
        return False, f"NIF deve ter exatamente 9 dígitos (tem {len(nif_clean)})"

    # Checksum módulo 11 oficial (Finanças PT)
    weights = [9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(nif_clean[i]) * weights[i] for i in range(8))

    remainder = total % 11
    expected_check_digit = 0 if remainder in (0, 1) else 11 - remainder
    actual_check_digit = int(nif_clean[8])

    if actual_check_digit != expected_check_digit:
        return False, (
            f"Checksum inválido (esperado {expected_check_digit}, "
            f"obtido {actual_check_digit})"
        )

    return True, ""


def classify_entity_type(nif: str) -> EntityType:
    """Classifica tipo de entidade pelo primeiro dígito"""
    if not nif or not nif[0].isdigit():
        return EntityType.OTHER

    first_digit = nif[0]
    if first_digit in ("1", "2", "3"):
        return EntityType.PERSON_SINGULAR_1
    elif first_digit == "5":
        return EntityType.LEGAL_ENTITY
    elif first_digit == "6":
        return EntityType.PUBLIC_ENTITY
    else:
        return EntityType.OTHER


def lookup_client_in_db(nif: str, db_path: str = "/opt/jfa/data/orcamentos.db") -> Tuple[bool, dict]:
    """
    Procura cliente na BD orcamentos.db

    Args:
        nif: NIF a procurar
        db_path: Caminho da BD (default: /opt/jfa/data/orcamentos.db)

    Returns:
        (encontrado, dados_cliente)
    """
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Procura em tabela 'clientes' ou 'customers' (ajustar conforme schema real)
        cursor.execute(
            "SELECT * FROM clientes WHERE nif = ? LIMIT 1",
            (nif,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            # Converte row para dict
            client_data = {k: row[k] for k in row.keys()}
            return True, client_data
        else:
            return False, {}

    except FileNotFoundError:
        return False, {"error": f"BD não encontrada em {db_path}"}
    except Exception as e:
        return False, {"error": f"Erro ao consultar BD: {str(e)}"}


def lookup_vies(nif: str, country_code: str = "PT") -> Optional[dict]:
    """
    Consulta VIES (VAT Information Exchange System) da UE.

    Args:
        nif: NIF (sem país)
        country_code: Código país (default: PT)

    Returns:
        Dict com dados VIES ou None se erro
    """
    try:
        # VIES SOAP endpoint
        url = "http://ec.europa.eu/taxation_customs/vies/vatServicePublic/checkVatService.wsdl"
        # Na prática, usar biblioteca Python: pip install zeep
        # Para agora, retorna aviso que não está implementado

        return {
            "implemented": False,
            "message": "VIES lookup requer biblioteca 'zeep' (pip install zeep)",
            "note": f"Poderia consultar: {country_code}{nif}",
        }
    except Exception as e:
        return {"error": f"Erro VIES: {str(e)}"}


def validate_and_lookup(nif: str, check_db: bool = True, check_vies: bool = False) -> NIFValidationResult:
    """
    Validação completa: checksum + tipo + BD + VIES

    Args:
        nif: NIF a validar
        check_db: Procurar na BD orcamentos.db
        check_vies: Consultar VIES (requer zeep)

    Returns:
        NIFValidationResult com todos os detalhes
    """
    nif_clean = nif.strip().replace(" ", "").replace("-", "")

    # 1. Validação checksum
    checksum_valid, error_msg = validate_nif(nif_clean)
    is_valid = checksum_valid

    # 2. Classificação
    entity_type = classify_entity_type(nif_clean)

    # 3. Procura BD (se checksum válido)
    is_client = None
    client_data = {}
    if check_db and checksum_valid:
        is_client, client_data = lookup_client_in_db(nif_clean)

    # 4. VIES (opcional)
    vies_data = {}
    if check_vies and checksum_valid:
        vies_result = lookup_vies(nif_clean)
        if vies_result:
            vies_data = vies_result

    return NIFValidationResult(
        nif=nif_clean,
        is_valid=is_valid,
        checksum_valid=checksum_valid,
        entity_type=entity_type,
        error_message=error_msg if not is_valid else None,
        is_client=is_client,
        client_data=client_data,
        vies_data=vies_data,
    )


if __name__ == "__main__":
    # Test
    test_nif = "511099177"
    print(f"\nTestando NIF: {test_nif}")
    result = validate_and_lookup(test_nif, check_db=True, check_vies=False)
    print(result)
