#!/bin/bash
# Script para executar testes RLS contra PostgreSQL real

set -e

echo "=== JFA RLS Integration Tests ==="
echo "Data: $(date)"
echo ""

# Verificar se PostgreSQL está acessível
echo "1. Verificando conexão PostgreSQL superuser..."
psql "postgresql://postgres:test-password@localhost:5433/jfa_test" -c "SELECT version();" 2>&1 | head -5

echo ""
echo "2. Verificando conexão PostgreSQL app_user (com RLS)..."
psql "postgresql://app_user:test-app-password@localhost:5433/jfa_test" -c "SELECT 'RLS enabled';" 2>&1

echo ""
echo "3. Executando pytest integration tests..."
cd /c/JFA_Unify/backend

# Executar testes com verbose e capture=no para ver output
pytest tests/integration/test_rls_isolation.py -v -m integration --tb=short

echo ""
echo "4. Resumo de cobertura RLS..."
pytest tests/integration/ -m integration --collect-only -q | grep "test_" | wc -l
echo "testes RLS encontrados"

echo ""
echo "=== Testes concluídos com sucesso ==="
