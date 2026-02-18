import { Button, Group, Select } from '@mantine/core'

import type { FilterSource, MonthString, WriteupFilters, YearString } from '../lib/api'

type Props = {
  filters: WriteupFilters
  onChange: (filters: WriteupFilters) => void
}

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: currentYear - 2025 + 1 }, (_, idx) => {
  const year = (currentYear - idx).toString()
  return { value: year, label: year }
})

const monthOptions = [
  { value: '', label: 'Todos os meses' },
  { value: '1', label: 'Janeiro' },
  { value: '2', label: 'Fevereiro' },
  { value: '3', label: 'Março' },
  { value: '4', label: 'Abril' },
  { value: '5', label: 'Maio' },
  { value: '6', label: 'Junho' },
  { value: '7', label: 'Julho' },
  { value: '8', label: 'Agosto' },
  { value: '9', label: 'Setembro' },
  { value: '10', label: 'Outubro' },
  { value: '11', label: 'Novembro' },
  { value: '12', label: 'Dezembro' },
]

const sourceOptions: { value: FilterSource; label: string }[] = [
  { value: 'all', label: 'Todos os sites' },
  { value: 'portswigger', label: 'PortSwigger' },
  { value: 'medium', label: 'Medium' },
  { value: 'hackerone', label: 'HackerOne' },
]

const initialFilters: WriteupFilters = {
  source: 'all',
  year: '',
  month: '',
}

export function FilterBar({ filters, onChange }: Props) {
  return (
    <div className="filters">
      <div className="filters-grid">
        <Select
          label="Fonte"
          data={sourceOptions}
          value={filters.source}
          onChange={(v) => onChange({ ...filters, source: (v as FilterSource) ?? 'all' })}
          comboboxProps={{ withinPortal: true, zIndex: 450 }}
        />
        <Select
          label="Ano"
          data={[{ value: '', label: 'Todos os anos' }, ...yearOptions]}
          value={filters.year}
          onChange={(v) => onChange({ ...filters, year: (v ?? '') as YearString })}
          comboboxProps={{ withinPortal: true, zIndex: 450 }}
        />
        <Select
          label="Mês"
          data={monthOptions}
          value={filters.month}
          onChange={(v) => onChange({ ...filters, month: (v ?? '') as MonthString })}
          comboboxProps={{ withinPortal: true, zIndex: 450 }}
        />
      </div>
      <Group justify="flex-end" mt="sm">
        <Button className="reset-filters" variant="light" radius="md" onClick={() => onChange(initialFilters)}>
          Limpar filtros
        </Button>
      </Group>
    </div>
  )
}
