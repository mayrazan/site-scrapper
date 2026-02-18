export type Source = 'portswigger' | 'medium' | 'hackerone'
export type FilterSource = Source | 'all'
export type MonthString = '' | `${1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12}`
export type YearString = '' | `${number}`

export type Writeup = {
  id: string
  source: Source
  title: string
  url: string
  author: string | null
  summary: string | null
  published_at: string
  created_at: string
}

export type WriteupFilters = {
  source: FilterSource
  year: YearString
  month: MonthString
}

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export async function fetchWriteups(filters: WriteupFilters): Promise<Writeup[]> {
  const params = new URLSearchParams()
  params.set('limit', '250')
  if (filters.source !== 'all') {
    params.set('source', filters.source)
  }
  if (filters.year) {
    params.set('year', filters.year)
  }
  if (filters.month) {
    params.set('month', filters.month)
  }

  const response = await fetch(`${API_BASE}/api/writeups?${params.toString()}`)
  if (!response.ok) {
    throw new Error(`Falha ao buscar writeups: ${response.status}`)
  }
  const data: unknown = await response.json()
  if (!Array.isArray(data)) {
    throw new Error('Resposta inválida da API')
  }
  return data as Writeup[]
}
