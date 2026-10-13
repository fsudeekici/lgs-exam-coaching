import { Link } from 'react-router-dom'
import KvkkNotice from '../components/KvkkNotice'

/** Public page with the KVKK privacy notice; readable without logging in. */
export default function KvkkPage() {
  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8">
      <main className="mx-auto max-w-2xl rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
        <Link to="/" className="text-sm text-indigo-700 hover:underline">
          ← LGS Koçluk
        </Link>
        <h1 className="mt-3 mb-4 text-2xl font-semibold text-slate-900">KVKK Aydınlatma Metni</h1>
        <KvkkNotice />
      </main>
    </div>
  )
}
