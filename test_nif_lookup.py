#!/usr/bin/env python3
import sqlite3
import sys

db_2025 = r'C:\JFA_Candidaturas\BuySell2025\analytics_2025.db'
db_2026 = r'C:\JFA_Candidaturas\BuySell2025\analytics_2026.db'
nif = '511099177'

print('='*70)
print(f'Procurando NIF {nif} nas BDs...')
print('='*70)

for db_path in [db_2025, db_2026]:
    year = "2025" if "2025" in db_path else "2026"
    print(f"\n[{year}] {db_path}")
    print("-" * 70)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Listar tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tabelas: {tables}")

        # Procurar em cada tabela
        found = False
        for table in tables:
            try:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]

                # Procurar por NIF em qualquer coluna
                for col in columns:
                    try:
                        query = f"SELECT * FROM {table} WHERE CAST({col} AS TEXT) = ?"
                        cursor.execute(query, (nif,))
                        rows = cursor.fetchall()
                        if rows:
                            print(f"\n✓ Encontrado em [{table}]:")
                            for row in rows:
                                data = {k: row[k] for k in row.keys()}
                                for key, val in data.items():
                                    print(f"    {key}: {val}")
                            found = True
                    except:
                        pass
            except:
                pass

        if not found:
            print(f"✗ NIF {nif} não encontrado em {year}")

        conn.close()

    except FileNotFoundError:
        print(f"✗ BD não encontrada: {db_path}")
    except Exception as e:
        print(f"✗ Erro: {e}")

print("\n" + "="*70)
