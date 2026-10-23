# Política de segurança

## Versões suportadas

Enquanto o projeto estiver em desenvolvimento, somente a versão presente na branch
`main` receberá correções de segurança.

## Reporte responsável

Não publique vulnerabilidades exploráveis em uma issue pública. Abra um aviso de
segurança privado no GitHub (`Security` → `Advisories` → `New draft advisory`) com:

- componente e versão afetados;
- passos mínimos para reprodução;
- impacto esperado;
- evidências sem dados sensíveis;
- correção sugerida, quando disponível.

Não inclua chaves privadas, tokens, credenciais ou dados pessoais. O mantenedor deve
confirmar o recebimento, classificar o risco e coordenar a divulgação após a correção.

## Baseline

O projeto adota o OWASP Top 10:2025 e usa o OWASP ASVS 5.0 como referência de
verificação. Os requisitos detalhados estão em `docs/security.md`.

## Escopo

Inclui a API, frontend, pipeline de dados, dependências, configuração de implantação
e workflows de CI/CD. Os dados públicos da ANAC não devem ser tratados como
instruções executáveis nem interpolados diretamente em SQL ou HTML.
