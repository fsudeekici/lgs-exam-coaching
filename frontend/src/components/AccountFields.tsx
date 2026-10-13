export const inputClass =
  'mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none'

export const labelClass = 'block text-sm font-medium text-slate-700'

interface Account {
  full_name: string
  email: string
  password: string
}

interface Props {
  value: Account
  onChange: (patch: Partial<Account>) => void
  /** When editing, the password may be left empty to keep the current one. */
  editing: boolean
}

/** Name, email and password inputs shared by the student and parent forms. */
export default function AccountFields({ value, onChange, editing }: Props) {
  return (
    <>
      <label className={labelClass}>
        Ad soyad
        <input
          required
          maxLength={255}
          value={value.full_name}
          onChange={(e) => onChange({ full_name: e.target.value })}
          className={inputClass}
        />
      </label>
      <label className={labelClass}>
        E-posta
        <input
          type="email"
          required
          maxLength={255}
          autoComplete="off"
          value={value.email}
          onChange={(e) => onChange({ email: e.target.value })}
          className={inputClass}
        />
      </label>
      <label className={labelClass}>
        Şifre
        <input
          type="password"
          required={!editing}
          minLength={8}
          autoComplete="new-password"
          placeholder={editing ? 'Değiştirmek için yazın' : 'En az 8 karakter'}
          value={value.password}
          onChange={(e) => onChange({ password: e.target.value })}
          className={inputClass}
        />
      </label>
    </>
  )
}

export function StatusBadge({ active }: { active: boolean }) {
  return active ? (
    <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-800">Aktif</span>
  ) : (
    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">Pasif</span>
  )
}
