export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50 to-white px-6 py-16">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-6 text-4xl font-bold text-emerald-700">
          About Health Hive
        </h1>

        <p className="mb-6 text-lg text-gray-700">
          <span className="font-semibold">Health Hive</span> is a community-based
          health and wellness platform that encourages users to lead a healthy
          and balanced lifestyle through planning, sharing, and collaboration.
        </p>

        <div className="mb-10 grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h2 className="mb-3 text-xl font-semibold text-emerald-600">
              Our Mission
            </h2>
            <p className="text-gray-600">
              To empower individuals with tools and community support to build
              sustainable healthy habits.
            </p>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h2 className="mb-3 text-xl font-semibold text-emerald-600">
              Our Vision
            </h2>
            <p className="text-gray-600">
              A connected community where health knowledge and motivation are
              shared openly.
            </p>
          </div>
        </div>

        <div className="mb-10">
          <h2 className="mb-4 text-2xl font-semibold text-emerald-600">
            What Health Hive Offers
          </h2>
          <ul className="list-inside list-disc space-y-2 text-gray-700">
            <li>Personalized health planning</li>
            <li>Explore wellness tips and routines</li>
            <li>Share health progress with others</li>
            <li>Community motivation and support</li>
          </ul>
        </div>

        <div className="text-center">
          <p className="mb-4 text-gray-700">
            Join Health Hive and take the first step toward a healthier life.
          </p>
          <div className="flex justify-center gap-4">
            <button className="rounded-2xl bg-emerald-600 px-6 py-3 text-white hover:bg-emerald-700">
              Create an Account
            </button>
            <button className="rounded-2xl border border-emerald-600 px-6 py-3 text-emerald-600 hover:bg-emerald-50">
              I Already Have an Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
