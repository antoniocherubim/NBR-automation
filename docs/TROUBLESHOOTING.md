# Solução de problemas

Diagnóstico e recuperação **segura**, sem expor originais sensíveis nem
executar ações destrutivas automáticas.

## Configuração privada ausente ou inválida

**Sintoma:** configuração/materialização de task `private_fixtures: required`
falha com configuração ausente, root inválido ou entrada faltando no store.

**O que fazer:**

1. Confirme que a task realmente precisa do corpus privado.
2. Configure o root com o helper (path absoluto, diretório real, sem symlink —
   inclusive sem barra final em symlink):

   ```bash
   NBR12721_PRIVATE_INPUTS="/caminho/absoluto/para/nbr12721-private-inputs" \
     bash scripts/private-fixtures/configure.sh
   bash scripts/private-fixtures/configure.sh --check
   ```

3. Não aponte o root para `/`, `//`, symlink, path com CR/newline, nem para
   **qualquer** checkout Git.
4. Não altere bytes no store para “passar” no hash — corrija a cópia autorizada.

Tasks com `private_fixtures: none` **não** exigem essa configuração. A suíte
pública e a CI também não.

## Gate da árvore pública falhou

**Sintoma:** `validate-public-tree.py` reporta path histórico, `inputs/private/`
ou digest de fixture privada.

**O que fazer:**

1. Confirme que os 14 originais não voltaram ao working tree nem ao commit.
2. Não copie bytes reais para `docs/`, testes, fixtures ou outputs.
3. Fixtures PDF/XLSX **sintéticas** com digest diferente continuam permitidas
   em localização pública explícita.
4. Lembre: limpar o working tree **não** remove objetos do histórico antigo.

## Inventário público inconsistente

**Sintoma:** `validate-gate.py` indica divergência entre inventário privado,
`SHA256SUMS` e source-manifest.

**O que fazer:**

1. **Não** edite esses três arquivos para “consertar” à força — eles devem
   permanecer byte a byte idênticos ao commit-base desta migração.
2. Restaure-os do commit-base se foram alterados acidentalmente.

## Materialização: tamanho ou hash divergente

**Sintoma:** `materialize.py` / verify falha em arquivo, tamanho ou digest.

**O que fazer:**

1. Rode `configure.sh --check` e confira o inventário.
2. Não “ajuste” bytes no store nem nas cópias.
3. Rematerialize após corrigir a fonte autorizada no store.

## Python incompatível

**Sintoma:** `ERROR: Python >= 3.12 obrigatório` durante a validação.

**O que fazer:** provisione Python 3.12+ fora dos scripts do repositório e repita os testes.

## Teste falhou

```bash
PYTHONPATH=src:scripts/private-fixtures python3 -m unittest discover -s tests -p 'test_*.py' -v
```

- Erros em `nbr12721.sources` → mapping, path, digest ou policy de output.
- Erros em `test_documentation` → link, heading ou whitespace final.
- Erros em `test_public_tree` / `test_ci_workflow` → snapshot candidato ou ZIP.
- **Não** altere inventários públicos nem reintroduza bytes privados.

## Ferramenta ausente

Provisione Python, Git, Bash e sha256sum no sistema. Os scripts do projeto não instalam pacotes.

## Mudanças ainda não integradas

O operador deve inspecionar o diff e executar todos os gates antes da integração. Nunca integre inventários alterados ou bytes privados reintroduzidos.

## Artifact.zip rejeitado

**Sintoma:** `validate-artifact-zip.py` falha com path histórico, digest
privado, traversal, duplicata ou CRC.

**O que fazer:** regenere o ZIP a partir do commit/snapshot sanitizado; não
injete conteúdo de `inputs/private/` nem dos 14 IDs históricos.
