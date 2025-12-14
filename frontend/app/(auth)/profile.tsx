// frontend/app/profile/page.tsx
"use client";
import { useState } from "react";
import Link from "next/link";

export default function Profile() {
  const [isEditing, setIsEditing] = useState(false);
  const [profile, setProfile] = useState({
    name: "John Doe",
    email: "john.doe@example.com",
    age: "28",
    height: "175",
    weight: "70",
    goal: "Lose weight and build muscle",
    activityLevel: "Moderate",
    bio: "Fitness enthusiast looking to maintain a healthy lifestyle"
  });

  const [editedProfile, setEditedProfile] = useState({ ...profile });

  const handleEdit = () => {
    setIsEditing(true);
    setEditedProfile({ ...profile });
  };

  const handleSave = () => {
    setProfile({ ...editedProfile });
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedProfile({ ...profile });
    setIsEditing(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setEditedProfile({
      ...editedProfile,
      [e.target.name]: e.target.value
    });
  };

  return (
    <main className="min-h-screen flex flex-col bg-gradient-to-br from-blue-50 via-white to-green-50">
      <header className="flex items-center justify-between px-8 py-6 backdrop-blur-sm bg-white/70 border-b border-gray-200">
        <Link href="/" className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-green-500 rounded-lg"></div>
          <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent">
            Health Hive
          </span>
        </Link>
        <nav className="flex items-center space-x-4 text-sm">
          <Link href="/" className="text-gray-700 hover:text-blue-600 transition-colors font-medium">
            Home
          </Link>
          <Link
            href="/profile"
            className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white font-semibold shadow-lg"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
            </svg>
          </Link>
        </nav>
      </header>

      <section className="flex-1 px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
            {/* Profile Header */}
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-8 py-12 text-white relative">
              <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
                <div className="w-32 h-32 rounded-full bg-white/20 backdrop-blur-sm border-4 border-white flex items-center justify-center text-5xl font-bold">
                  {profile.name.charAt(0)}
                </div>
                <div className="text-center md:text-left flex-1">
                  <h1 className="text-3xl font-bold mb-2">{profile.name}</h1>
                  <p className="text-blue-100 mb-4">{profile.email}</p>
                  <div className="flex flex-wrap gap-3 justify-center md:justify-start">
                    <span className="bg-white/20 backdrop-blur-sm px-4 py-1.5 rounded-full text-sm">
                      🎯 {profile.goal}
                    </span>
                    <span className="bg-white/20 backdrop-blur-sm px-4 py-1.5 rounded-full text-sm">
                      📊 {profile.activityLevel} Activity
                    </span>
                  </div>
                </div>
                {!isEditing && (
                  <button
                    onClick={handleEdit}
                    className="absolute top-4 right-4 bg-white/20 backdrop-blur-sm hover:bg-white/30 px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                    </svg>
                    Edit Profile
                  </button>
                )}
              </div>
            </div>

            {/* Profile Content */}
            <div className="p-8">
              {isEditing ? (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Name</label>
                      <input
                        type="text"
                        name="name"
                        value={editedProfile.name}
                        onChange={handleChange}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                      <input
                        type="email"
                        name="email"
                        value={editedProfile.email}
                        onChange={handleChange}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Age</label>
                      <input
                        type="number"
                        name="age"
                        value={editedProfile.age}
                        onChange={handleChange}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Activity Level</label>
                      <select
                        name="activityLevel"
                        value={editedProfile.activityLevel}
                        onChange={handleChange}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                      >
                        <option>Sedentary</option>
                        <option>Light</option>
                        <option>Moderate</option>
                        <option>Active</option>
                        <option>Very Active</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Height (cm)</label>
                      <input
                        type="number"
                        name="height"
                        value={editedProfile.height}
                        onChange={handleChange}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Weight (kg)</label>
                      <input
                        type="number"
                        name="weight"
                        value={editedProfile.weight}
                        onChange={handleChange}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Health Goal</label>
                    <input
                      type="text"
                      name="goal"
                      value={editedProfile.goal}
                      onChange={handleChange}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Bio</label>
                    <textarea
                      name="bio"
                      value={editedProfile.bio}
                      onChange={handleChange}
                      rows={4}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                    />
                  </div>

                  <div className="flex gap-4 pt-4">
                    <button
                      onClick={handleSave}
                      className="flex-1 bg-gradient-to-r from-blue-600 to-blue-700 text-white py-3 rounded-lg font-semibold hover:shadow-lg hover:scale-105 transition-all"
                    >
                      Save Changes
                    </button>
                    <button
                      onClick={handleCancel}
                      className="flex-1 border-2 border-gray-300 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">About Me</h2>
                    <p className="text-gray-600">{profile.bio}</p>
                  </div>

                  <div>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Health Stats</h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4">
                        <div className="text-2xl mb-1">🎂</div>
                        <div className="text-2xl font-bold text-blue-900">{profile.age}</div>
                        <div className="text-sm text-blue-700">Years Old</div>
                      </div>
                      <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4">
                        <div className="text-2xl mb-1">📏</div>
                        <div className="text-2xl font-bold text-green-900">{profile.height}</div>
                        <div className="text-sm text-green-700">cm</div>
                      </div>
                      <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4">
                        <div className="text-2xl mb-1">⚖️</div>
                        <div className="text-2xl font-bold text-purple-900">{profile.weight}</div>
                        <div className="text-sm text-purple-700">kg</div>
                      </div>
                      <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl p-4">
                        <div className="text-2xl mb-1">🔥</div>
                        <div className="text-xl font-bold text-orange-900">{profile.activityLevel}</div>
                        <div className="text-sm text-orange-700">Activity</div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">My Journey</h2>
                    <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 border-l-4 border-blue-600">
                      <p className="text-gray-700">{profile.goal}</p>
                    </div>
                  </div>
                </div>
              )}
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