import { Badge, Card, Group, Text, Title } from '@mantine/core'

import type { Writeup } from '../lib/api'

type Props = {
  item: Writeup
}

const sourceLabel: Record<Writeup['source'], string> = {
  portswigger: 'PortSwigger',
  medium: 'Medium',
  hackerone: 'HackerOne',
}

export function WriteupCard({ item }: Props) {
  const date = new Date(item.published_at)
  const cleanSummary = item.summary?.replace(/<[^>]+>/g, '')

  return (
    <a className="card-link" href={item.url} target="_blank" rel="noreferrer">
      <Card className={`writeup-card source-${item.source}`} radius="md" shadow="sm" padding="lg">
        <Group justify="space-between" align="start">
          <Badge variant="light">{sourceLabel[item.source]}</Badge>
          <Text size="xs" c="dimmed">
            {date.toLocaleDateString('pt-BR')}
          </Text>
        </Group>

        <Title order={4} className="writeup-title">
          {item.title}
        </Title>

        {cleanSummary ? (
          <Text size="sm" lineClamp={3} c="dimmed">
            {cleanSummary}
          </Text>
        ) : (
          <Text size="sm" c="dimmed">
            Sem resumo disponível.
          </Text>
        )}

        <Group justify="space-between" mt="md" align="center">
          {item.author ? (
            <Text size="xs" c="dimmed">
              por {item.author}
            </Text>
          ) : (
            <Text size="xs" c="dimmed">
              Autor não informado
            </Text>
          )}
          <Text className="card-cta" size="xs">
            Abrir análise
          </Text>
        </Group>
      </Card>
    </a>
  )
}
