// frontend/app/consultants/page.tsx
"use client";
import { useState } from "react";
import Link from "next/link";

interface Consultant {
  id: number;
  name: string;
  specialty: string;
  experience: number;
  rating: number;
  reviews: number;
  bio: string;
  image: string;
  price: number;
  availability: string[];
}

export default function Consultants() {
  const [selectedSpecialty, setSelectedSpecialty] = useState("All");

  const consultants: Consultant[] = [
    {
      id: 1,
      name: "Dr. Sarah Johnson",
      specialty: "Nutritionist",
      experience: 8,
      rating: 4.9,
      reviews: 127,
      bio: "Specialized in weight management and sports nutrition",
      image: "SJ",
      price: 50,
      availability: ["Mon", "Wed", "Fri"]
    },
    {
      id: 2,
      name: "Dr. Michael Chen",
      specialty: "Fitness Trainer",
      experience: 5,
      rating: 4.8,
      reviews: 93,
      bio: "Expert in strength training and muscle building",
      image: "MC",
      price: 45,
      availability: ["Tue", "Thu", "Sat"]
    },
    {
      id: 3,
      name: "Dr. Emily Rodriguez",
      specialty: "Mental Health",
      experience: 12,
      rating: 5.0,
      reviews: 201,
      bio: "Helping clients with stress management and mindfulness",
      image: "ER",
      price: 60,
      availability: ["Mon", "Tue", "Wed", "Thu"]
    },
    {
      id: 4,
      name: "Dr. James Wilson",
      specialty: "Physical Therapist",
      experience: 10,
      rating: 4.7,
      reviews: 156,
      bio: "Specialized in injury recovery and mobility improvement",
      image: "JW",
      price: 55,
      availability: ["Wed", "Thu", "Fri", "Sat"]
    },
    {
      id: 5,
      name: "Dr. Lisa Martinez",
      specialty: "Nutritionist",
      experience: 6,
      rating: 4.9,
      reviews: 89,
      bio: "Focus on plant-based diets and sustainable eating",
      image: "LM",
      price: 48,
      availability: ["Mon", "Tue", "Fri"]
    },
    {
      id: 6,
      name: "Dr. David Kim",
      specialty: "Yoga Instructor",
      experience: 7,
      rating: 4.8,
      reviews: 112,
      bio: "Teaching holistic wellness through yoga and meditation",
      image: "DK",
      price: 40,
      availability: ["Tue", "Thu", "Sat", "Sun"]
    }
  ];

  const specialties = ["All", "Nutritionist", "Fitness Trainer", "Mental Health", "Physical Therapist", "Yoga Instructor"];

  const filteredConsultants = selectedSpecialty === "All" 
    ? consultants 
    : consultants.filter(c => c.specialty === selectedSpecialty);

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
          <Link href="/consultants" className="text-blue-600 font-medium">
            Consultants
          </Link>
          <Link
            href="/profile"
            className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white font-semibold hover:shadow-lg hover:scale-110 transition-all duration-200"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
            </svg>
          </Link>
        </nav>
      </header>

      <section className="flex-1 px-4 py-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Our Expert Consultants
              </span>
            </h1>
            <p className="text-gray-600 text-lg">Find the perfect health professional for your journey</p>
          </div>

          {/* Specialty Filter */}
          <div className="flex flex-wrap justify-center gap-3 mb-8">
            {specialties.map((specialty) => (
              <button
                key={specialty}
                onClick={() => setSelectedSpecialty(specialty)}
                className={`px-6 py-2.5 rounded-full font-medium transition-all duration-200 ${
                  selectedSpecialty === specialty
                    ? "bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg scale-105"
                    : "bg-white text-gray-700 hover:bg-gray-50 border border-gray-200"
                }`}
              >
                {specialty}
              </button>
            ))}
          </div>

          {/* Consultants Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredConsultants.map((consultant) => (
              <div
                key={consultant.id}
                className="bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden group"
              >
                <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-6 relative">
                  <div className="w-24 h-24 rounded-full bg-white/20 backdrop-blur-sm border-4 border-white mx-auto flex items-center justify-center text-3xl font-bold text-white">
                    {consultant.image}
                  </div>
                  <div className="absolute top-4 right-4 bg-white/20 backdrop-blur-sm px-3 py-1 rounded-full text-white text-sm font-medium">
                    ${consultant.price}/hr
                  </div>
                </div>

                <div className="p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-1">{consultant.name}</h3>
                  <p className="text-blue-600 font-medium mb-3">{consultant.specialty}</p>
                  
                  <div className="flex items-center gap-4 mb-3 text-sm text-gray-600">
                    <span className="flex items-center gap-1">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-yellow-500" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      {consultant.rating} ({consultant.reviews})
                    </span>
                    <span>💼 {consultant.experience} yrs</span>
                  </div>

                  <p className="text-gray-600 text-sm mb-4">{consultant.bio}</p>

                  <div className="mb-4">
                    <p className="text-sm font-medium text-gray-700 mb-2">Available:</p>
                    <div className="flex flex-wrap gap-2">
                      {consultant.availability.map((day) => (
                        <span
                          key={day}
                          className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium"
                        >
                          {day}
                        </span>
                      ))}
                    </div>
                  </div>

                  <Link
                    href={`/consultants/${consultant.id}/book`}
                    className="w-full block text-center bg-gradient-to-r from-blue-600 to-blue-700 text-white py-3 rounded-lg font-semibold hover:shadow-lg hover:scale-105 transition-all duration-200"
                  >
                    Book Appointment
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {filteredConsultants.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">No consultants found in this category</p>
            </div>
          )}
        </div>
      </section>

      <footer className="py-6 text-center text-sm text-gray-500 border-t border-gray-200 bg-white/50 backdrop-blur-sm">
        <p>© {new Date().getFullYear()} Health Hive. All rights reserved.</p>
      </footer>
    </main>
  );
}