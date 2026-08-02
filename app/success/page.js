import Link from "next/link";

export default function SuccessPage() {
  return (
    <main className="min-h-screen bg-gray-100 flex items-center justify-center p-8">
      <div className="bg-white max-w-xl w-full rounded-xl shadow p-8 text-center">
        <div className="text-7xl mb-6">✅</div>

        <h1 className="text-3xl font-bold text-green-700 mb-4">
          Application Submitted
        </h1>

        <p className="text-gray-600 mb-8">
          Thank you for helping a rescued animal find a loving home.
          The shelter will review your request soon.
        </p>

        <Link
          href="/dashboard"
          className="bg-green-600 text-white px-6 py-3 rounded-lg"
        >
          Back to Dashboard
        </Link>
      </div>
    </main>
  );
}