import { useState } from "react"
import { useParams, Link } from "react-router-dom"

const API_URL = import.meta.env.VITE_API_URL || "https://homiest-simonne-unofficious.ngrok-free.dev"

export function ProofOfPaymentPage() {
  const { loanId } = useParams<{ loanId: string }>()
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle")
  const [message, setMessage] = useState<string>("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!loanId || !file) {
      setStatus("error")
      setMessage("Please select a file to upload.")
      return
    }
    setStatus("uploading")
    setMessage("")
    try {
      const formData = new FormData()
      formData.append("file", file)
      const res = await fetch(`${API_URL}/api/lending/loans/${encodeURIComponent(loanId)}/proof`, {
        method: "POST",
        body: formData,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStatus("error")
        const d = data.detail
        const msg = Array.isArray(d) ? (d[0]?.msg || d[0]?.loc?.join(" ") || "Upload failed.") : (d || data.error_message || "Upload failed.")
        setMessage(typeof msg === "string" ? msg : "Upload failed.")
        return
      }
      setStatus("success")
      setMessage("Proof of payment recorded. Thank you!")
      setFile(null)
    } catch (err) {
      setStatus("error")
      setMessage(err instanceof Error ? err.message : "Upload failed.")
    }
  }

  const accept = "image/*,application/pdf"

  return (
    <div className="min-h-screen min-h-[100dvh] bg-gray-50 flex flex-col items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-sm border border-gray-200 p-4 sm:p-6 md:p-8">
        <div className="text-center mb-4 sm:mb-6">
          <h1 className="text-lg sm:text-xl font-semibold text-gray-900">Proof of payment</h1>
          <p className="mt-2 text-sm text-gray-600">
            You’ve sent the loan money. Upload a photo or PDF of your proof (e.g. transfer screenshot).
          </p>
          {loanId && (
            <p className="mt-1 text-xs text-gray-500 font-mono">Loan: {loanId}</p>
          )}
        </div>

        {!loanId ? (
          <div className="text-center text-gray-500 text-sm">
            <p>Missing loan ID in the link.</p>
            <p className="mt-2">
              Use the link shared with you in WhatsApp (e.g. …/pop/&lt;loanId&gt;).
            </p>
            <Link to="/" className="mt-4 inline-block text-blue-600 hover:underline text-sm">
              ← Back to chat
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="pop-file" className="block text-sm font-medium text-gray-700 mb-1">
                Photo or PDF
              </label>
              <input
                id="pop-file"
                type="file"
                accept={accept}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-kasi-green file:text-white hover:file:bg-kasi-green-light"
              />
            </div>

            {status === "success" && (
              <div className="rounded-lg bg-green-50 text-green-800 text-sm p-3">
                {message}
              </div>
            )}
            {status === "error" && message && (
              <div className="rounded-lg bg-red-50 text-red-800 text-sm p-3">
                {message}
              </div>
            )}

            <button
              type="submit"
              disabled={status === "uploading" || !file}
              className="w-full py-2.5 px-4 rounded-xl bg-kasi-green text-white font-medium text-sm hover:bg-kasi-green-light disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {status === "uploading" ? "Uploading…" : "Upload proof"}
            </button>
          </form>
        )}

        {loanId && status !== "success" && (
          <p className="mt-6 text-center">
            <Link to="/" className="text-sm text-blue-600 hover:underline">
              ← Back to chat
            </Link>
          </p>
        )}
      </div>
    </div>
  )
}
