export default function Table({
  columns,
  rows,
  empty = 'No records to show.',
  onRowClick,
  selectedKey,
}) {
  if (!rows.length) {
    return <p className="py-8 text-center text-sm text-ink-600">{empty}</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead>
          <tr className="border-b border-ink-200 text-xs font-medium uppercase tracking-wide text-ink-500">
            {columns.map((column) => (
              <th key={column.key} className="px-3 py-3 font-medium">
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const rowKey = row.rowKey || row.emp_id || row.id
            const selected = selectedKey != null && selectedKey === rowKey
            return (
              <tr
                key={rowKey}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={`border-b border-ink-100 last:border-0 ${
                  onRowClick ? 'cursor-pointer hover:bg-gold-100' : ''
                } ${selected ? 'bg-gold-100' : ''}`}
              >
                {columns.map((column) => (
                  <td key={column.key} className="px-3 py-3 text-ink-900">
                    {column.render ? column.render(row) : row[column.key]}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
