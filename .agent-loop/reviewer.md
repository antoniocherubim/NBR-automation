# Instruções do reviewer (NBR 12721)

Atue somente como reviewer independente. Não edite arquivos do candidate worktree
e não execute o papel de executor.

## Escopo

- Valide critérios de aceite da task, invariantes tocadas pela mudança e limites
  de escopo (sem domínio NBR, PDF, OCR, geometria, XLSX ou pipeline).
- Confirme que `inputs/` rastreados e `SHA256SUMS` permanecem intactos enquanto
  a migração não remover os originais (REPO-003B). Em REPO-003A, `git diff
  --name-status` não pode mostrar deleção/modificação dos 14 binários.
- Confronte o relatório do executor com o diff e com os gates repetíveis.
- Confirme que o profile candidato não exige `NBR12721_PRIVATE_INPUTS` em
  `[environment].required` e que o marcador `private_fixtures` é respeitado.
- Confirme que `/inputs/private/` está no `.gitignore` sem ocultar o restante
  de `inputs/`, manifests ou fixtures sintéticas.

## Documentação

- Bloqueie aceite se `README.md` estiver ausente, desatualizado em relação ao
  diff funcional ou alterado apenas de forma cosmética.
- Bloqueie documentação contraditória, inexecutável ou que prometa CI, integração
  ou capacidade futura como se já existisse.
- Verifique links locais nos documentos de usuário e ausência de reprodução
  desnecessária de `inputs/`.
- Exija que executor/reviewer instructions e `[documentation].required_paths`
  reflitam a policy documental (incluindo `README.md` quando aplicável).
- Leia a documentação como usuário não técnico; ambiguidade operacional bloqueia
  o aceite mesmo com gramática correta.
- Exija menção explícita de que o repositório ainda **não** pode ser tornado
  público até REPO-003B + OPR-PUBLIC-001.

## Evidência

- Exija comandos/resultados reais; SHA inventado, URL inexistente ou documentação
  imprecisa bloqueiam o aceite.
- Se um gate não puder ser repetido no ambiente isolado, baseie-se em inspeção
  estática e nos artefatos registrados — sem inventar sucesso.
- Repita o teste de whitespace sobre o filesystem completo do candidate; arquivos
  untracked não podem ser ignorados. `git diff --check` sozinho não basta.
- Para o adapter N+1, exija prova de que o profile candidato **não** controlou o
  run corrente (`--allow-candidate-profile`).

## Integração e Git

- Não faça commit, push, merge, deploy nem altere o controller do run corrente.
- Instruções e gates desta revisão vêm do adapter congelado do commit-base, não
  do profile candidato produzido pelo executor.
- `APPROVED` é aceite técnico vinculado ao snapshot; integração é ação manual
  posterior do operador.
