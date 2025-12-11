// frontend/app/page.tsx
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col">
      <header className="flex items-center justify-between px-8 py-4 border-b">
        <div className="text-xl font-bold">Health Hive</div>
        <nav className="space-x-4 text-sm">
          <Link href="/login" className="hover:underline">
            Login
          </Link>
          <Link
            href="/register"
            className="rounded-md bg-blue-600 px-4 py-2 text-white text-sm font-medium hover:bg-blue-700"
          >
            Get Started
          </Link>
        </nav>
      </header>

      <section className="flex-1 flex items-center justify-center px-4">
        <div className="max-w-2xl text-center space-y-6">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight">
            Explore Plan & Share your health
          </h1>
          <p className="text-gray-600 text-base md:text-lg">
            A community based software encouging users to lead a healthy life .
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="/register"
              className="rounded-md bg-blue-600 px-6 py-3 text-white font-medium hover:bg-blue-700"
            >
              Create an account
            </Link>
            <Link
              href="/login"
              className="rounded-md border border-gray-300 px-6 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              I already have an account
            </Link>
          </div>
        </div>
      </section>

      <footer className="py-4 text-center text-xs text-gray-500 border-t">
        © {new Date().getFullYear()} YourApp. All rights reserved.
      </footer>
    </main>
  );
}
