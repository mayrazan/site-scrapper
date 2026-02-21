import {
  Alert,
  AppShell,
  Container,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { useMemo, useState } from 'react'

import { FilterBar } from './components/FilterBar'
import { WriteupCard } from './components/WriteupCard'
import { useWriteups } from './hooks/useWriteups'
import type { WriteupFilters } from './lib/api'

const initialFilters: WriteupFilters = {
  source: 'all',
  year: '',
  month: '',
  favorites: false,
}

export function App() {
  const [filters, setFilters] = useState<WriteupFilters>(initialFilters)
  const { data, isPending, error } = useWriteups(filters)

  const sorted = useMemo(
    () =>
      [...(data ?? [])].sort((a, b) => {
        return new Date(b.published_at).getTime() - new Date(a.published_at).getTime()
      }),
    [data],
  )

  const filtered = useMemo(
    () => (filters.favorites ? sorted.filter((item) => item.is_favorite) : sorted),
    [sorted, filters.favorites],
  )

  const metrics = useMemo(() => {
    const uniqueSources = new Set(sorted.map((item) => item.source)).size
    const thisMonth = new Date().getMonth()
    const thisYear = new Date().getFullYear()
    const monthlyCount = sorted.filter((item) => {
      const date = new Date(item.published_at)
      return date.getMonth() === thisMonth && date.getFullYear() === thisYear
    }).length

    const freshest = sorted[0]?.published_at
      ? new Date(sorted[0].published_at).toLocaleDateString('pt-BR')
      : '-'

    return {
      total: sorted.length,
      sources: uniqueSources,
      monthlyCount,
      freshest,
    }
  }, [sorted])

  const showFavoritesEmpty = !isPending && !error && filtered.length === 0 && filters.favorites

  return (
    <AppShell>
      <div className="hero-bg" aria-hidden="true" />
      <Container size="lg" py="xl" className="reader-container">
        <Stack gap="lg">
          <header className="hero-header">
            <Group justify="space-between" align="start" className="hero-topline">
              <Text className="kicker">Bug Bounty Radar</Text>
              <Text className="live-pill">Atualização diária</Text>
            </Group>
            <Title className="page-title" order={1}>
              Intelligence feed para write-ups de segurança
            </Title>
            <Text className="hero-subtitle">
              Curadoria em tempo real de PortSwigger, Medium e HackerOne com leitura otimizada para
              triagem rápida.
            </Text>
          </header>

          <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="sm">
            <Paper className="metric-card" p="md" radius="md">
              <Text className="metric-label">Registros</Text>
              <Text className="metric-value">{metrics.total}</Text>
            </Paper>
            <Paper className="metric-card" p="md" radius="md">
              <Text className="metric-label">Fontes ativas</Text>
              <Text className="metric-value">{metrics.sources}</Text>
            </Paper>
            <Paper className="metric-card" p="md" radius="md">
              <Text className="metric-label">Publicados no mês</Text>
              <Text className="metric-value">{metrics.monthlyCount}</Text>
            </Paper>
            <Paper className="metric-card" p="md" radius="md">
              <Text className="metric-label">Mais recente</Text>
              <Text className="metric-value metric-date">{metrics.freshest}</Text>
            </Paper>
          </SimpleGrid>

          <FilterBar filters={filters} onChange={setFilters} />

          {isPending ? (
            <Paper className="status-panel" p="md">
              <Group gap="xs">
                <Loader size="sm" />
                <Text size="sm">Carregando write-ups...</Text>
              </Group>
            </Paper>
          ) : null}

          {error ? (
            <Alert color="red" title="Erro ao carregar" radius="md">
              {(error as Error).message}
            </Alert>
          ) : null}

          {showFavoritesEmpty ? (
            <Text size="sm" c="dimmed">
              Nenhum favorito ainda. Clique na estrela de um writeup para salvá-lo.
            </Text>
          ) : null}

          {!isPending && !error && !showFavoritesEmpty ? (
            <>
              <Text size="sm" className="result-count">
                {filtered.length} resultados encontrados
              </Text>
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                {filtered.map((item) => (
                  <WriteupCard key={item.url} item={item} />
                ))}
              </SimpleGrid>
            </>
          ) : null}
        </Stack>
      </Container>
    </AppShell>
  )
}
