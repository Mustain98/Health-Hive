// frontend/app/page.tsx
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col bg-gradient-to-br from-blue-50 via-white to-green-50">
      <header className="flex items-center justify-between px-8 py-6 backdrop-blur-sm bg-white/70 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-green-500 rounded-lg"></div>
          <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent">
            Health Hive
          </span>
        </div>
        <nav className="flex items-center space-x-4 text-sm">
          <Link href="/login" className="text-gray-700 hover:text-blue-600 transition-colors font-medium">
            Login
          </Link>
          <Link
            href="/register"
            className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 px-5 py-2.5 text-white text-sm font-medium hover:shadow-lg hover:scale-105 transition-all duration-200"
          >
            Get Started
          </Link>
        </nav>
      </header>

      <section className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="max-w-4xl text-center space-y-8">
          <div className="space-y-4">
            <div className="inline-block">
              <span className="inline-flex items-center rounded-full bg-blue-100 px-4 py-1.5 text-sm font-medium text-blue-700 mb-4">
                🌟 Your Health, Your Community
              </span>
            </div>
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight">
              <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-green-600 bg-clip-text text-transparent">
                Explore, Plan & Share
              </span>
              <br />
              <span className="text-gray-900">Your Health Journey</span>
            </h1>
            <p className="text-gray-600 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
              A community-based platform encouraging users to lead a healthier, 
              happier life together. Track your progress, share your wins, and inspire others.
            </p>
          </div>

          <div className="flex flex-wrap justify-center gap-4 pt-4">
            <Link
              href="/register"
              className="group rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 px-8 py-4 text-white font-semibold hover:shadow-2xl hover:scale-105 transition-all duration-300 flex items-center space-x-2"
            >
              <span>Create an account</span>
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </Link>
            <Link
              href="/login"
              className="rounded-xl border-2 border-gray-300 bg-white px-8 py-4 text-gray-700 font-semibold hover:border-blue-600 hover:text-blue-600 hover:shadow-lg transition-all duration-300"
            >
              I already have an account
            </Link>
          </div>

          <div className="pt-12 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-3xl mx-auto">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow">
              <div className="text-4xl mb-3">💪</div>
              <h3 className="font-bold text-lg mb-2 text-gray-900">Track Progress</h3>
              <p className="text-gray-600 text-sm">Monitor your health goals and celebrate milestones</p>
            </div>
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow">
              <div className="text-4xl mb-3">🤝</div>
              <h3 className="font-bold text-lg mb-2 text-gray-900">Join Community</h3>
              <p className="text-gray-600 text-sm">Connect with others on similar health journeys</p>
            </div>
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow">
              <div className="text-4xl mb-3">📊</div>
              <h3 className="font-bold text-lg mb-2 text-gray-900">Share Insights</h3>
              <p className="text-gray-600 text-sm">Inspire others with your achievements and tips</p>
            </div>
          </div>
        </div>
      </section>

      <footer className="py-6 text-center text-sm text-gray-500 border-t border-gray-200 bg-white/50 backdrop-blur-sm">
        <p>© {new Date().getFullYear()} Health Hive. All rights reserved.</p>
      </footer>
    </main>
  );
}