export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50 to-white px-6 py-16">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-6 text-4xl font-bold text-emerald-700">
          About Health Hive
        </h1>

        <p className="mb-6 text-lg text-gray-700">
          <span className="font-semibold">Health Hive</span> is a community-based
          health and wellness platform designed to encourage individuals to lead
          healthier, more balanced lives. We believe that sustainable health
          improvement happens when people learn, plan, and grow together.
        </p>

        <div className="mb-10 grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h2 className="mb-3 text-xl font-semibold text-emerald-600">
              Our Mission
            </h2>
            <p className="text-gray-600">
              Our mission is to empower users with the right tools, knowledge, and
              community support to make informed health decisions and build
              long-lasting healthy habits.
            </p>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <h2 className="mb-3 text-xl font-semibold text-emerald-600">
              Our Vision
            </h2>
            <p className="text-gray-600">
              We envision a connected world where people openly share experiences,
              motivate one another, and take proactive steps toward physical and
              mental well-being.
            </p>
          </div>
        </div>

        <div className="mb-10">
          <h2 className="mb-4 text-2xl font-semibold text-emerald-600">
            What You Can Do with Health Hive
          </h2>
          <ul className="list-inside list-disc space-y-2 text-gray-700">
            <li>Create and manage personalized health and wellness plans</li>
            <li>Explore health tips, routines, and best practices</li>
            <li>Share progress, experiences, and success stories</li>
            <li>Connect with a supportive, like-minded community</li>
            <li>Stay motivated through collective learning and encouragement</li>
          </ul>
        </div>

        <div className="mb-10 rounded-2xl bg-emerald-50 p-6">
          <h2 className="mb-3 text-2xl font-semibold text-emerald-700">
            Why Health Hive?
          </h2>
          <p className="text-gray-700">
            Unlike traditional health apps that focus only on tracking, Health Hive
            emphasizes community, collaboration, and shared growth. By combining
            planning tools with social interaction, we help users stay consistent
            and accountable on their wellness journey.
          </p>
        </div>

        <div className="text-center">
          <h2 className="mb-3 text-2xl font-semibold text-emerald-600">
            Get Started Today
          </h2>
          <p className="mb-6 text-gray-700">
            Join Health Hive and become part of a growing community that believes
            health is better when it is shared.
          </p>
          <div className="flex justify-center gap-4">
            <button className="rounded-2xl bg-emerald-600 px-6 py-3 font-medium text-white shadow hover:bg-emerald-700">
              Create an Account
            </button>
            <button className="rounded-2xl border border-emerald-600 px-6 py-3 font-medium text-emerald-600 hover:bg-emerald-50">
              I Already Have an Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
