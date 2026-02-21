import { useState } from 'react'
import { ActionIcon, Badge, Card, Group, Text, Title } from '@mantine/core'
import { notifications } from '@mantine/notifications'

import type { Writeup } from '../lib/api'
import { patchFavorite } from '../lib/api'

type Props = {
  item: Writeup
}

const sourceLabel: Record<Writeup['source'], string> = {
  portswigger: 'PortSwigger',
  medium: 'Medium',
  hackerone: 'HackerOne',
}

function StarIcon({ filled }: { filled: boolean }) {
  if (filled) {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
      </svg>
    )
  }
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  )
}

export function WriteupCard({ item }: Props) {
  const date = new Date(item.published_at)
  const cleanSummary = item.summary?.replace(/<[^>]+>/g, '')
  const [isFavorite, setIsFavorite] = useState(item.is_favorite ?? false)
  const [isLoading, setIsLoading] = useState(false)

  async function handleToggleFavorite(e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (isLoading) return
    const next = !isFavorite
    setIsFavorite(next)
    setIsLoading(true)
    try {
      await patchFavorite(item.id, next)
    } catch {
      setIsFavorite(!next)
      notifications.show({ color: 'red', message: 'Erro ao salvar favorito.' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <a className="card-link" href={item.url} target="_blank" rel="noreferrer">
      <Card className={`writeup-card source-${item.source}`} radius="md" shadow="sm" padding="lg">
        <Group justify="space-between" align="start">
          <Badge variant="light">{sourceLabel[item.source]}</Badge>
          <Group gap="xs" align="center">
            <Text size="xs" c="dimmed">
              {date.toLocaleDateString('pt-BR')}
            </Text>
            <ActionIcon
              variant="transparent"
              size="sm"
              disabled={isLoading}
              onClick={handleToggleFavorite}
              aria-label={isFavorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
              c={isFavorite ? 'yellow' : 'gray'}
            >
              <StarIcon filled={isFavorite} />
            </ActionIcon>
          </Group>
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
