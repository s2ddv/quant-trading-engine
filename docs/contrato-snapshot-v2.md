# Snapshot sintético — esquema 2

O esquema 2 conserva o [contrato F0 do esquema 1](contrato-snapshot-v1.md)
e acrescenta somente `exit_cash_per_share` a ações de deslistagem. O valor é
decimal finito e não negativo por ação, em BRL. Sua presença exige
`pay_session` no calendário, na ex-data ou depois dela. A ação deve estar
disponível antes da abertura da ex-data quando houver posição; anúncio tardio
impede reconstruir o direito e interrompe a execução.

Sem o campo, a deslistagem não tem preço ou pagamento presumido. Snapshots
do esquema 1 permanecem válidos e rejeitam o campo novo. O SHA-256 canônico
continua identificando todo o conteúdo validado, sem autenticar a fonte.
