// frontend/app/consultants/[id]/book/page.tsx
"use client";
import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

interface TimeSlot {
  time: string;
  available: boolean;
}

export default function BookAppointment() {
  const params = useParams();
  const consultantId = params.id;

  // Mock consultant data - in real app, fetch based on consultantId
  const consultant = {
    id: consultantId,
    name: "Dr. Sarah Johnson",
    specialty: "Nutritionist",
    price: 50,
    image: "SJ"
  };

  const [selectedDate, setSelectedDate] = useState("");
  const [selectedTime, setSelectedTime] = useState("");
  const [appointmentType, setAppointmentType] = useState("video");
  const [notes, setNotes] = useState("");
  const [showConfirmation, setShowConfirmation] = useState(false);

  // Generate next 7 days
  const getNextDays = () => {
    const days = [];
    const today = new Date();
    for (let i = 0; i < 7; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() + i);
      days.push({
        date: date.toISOString().split('T')[0],
        day: date.toLocaleDateString('en-US', { weekday: 'short' }),
        dayNum: date.getDate(),
        month: date.toLocaleDateString('en-US', { month: 'short' })
      });
    }
    return days;
  };

  const availableDays = getNextDays();

  // Time slots for selected date
  const timeSlots: TimeSlot[] = [
    { time: "09:00 AM", available: true },
    { time: "10:00 AM", available: true },
    { time: "11:00 AM", available: false },
    { time: "12:00 PM", available: true },
    { time: "02:00 PM", available: true },
    { time: "03:00 PM", available: true },
    { time: "04:00 PM", available: false },
    { time: "05:00 PM", available: true }
  ];

  const handleBookAppointment = () => {
    if (selectedDate && selectedTime) {
      setShowConfirmation(true);
    }
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
          <Link href="/consultants" className="text-gray-700 hover:text-blue-600 transition-colors font-medium">
            ← Back to Consultants
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

      {!showConfirmation ? (
        <section className="flex-1 px-4 py-8">
          <div className="max-w-5xl mx-auto">
            <div className="mb-8">
              <Link href="/consultants" className="text-blue-600 hover:text-blue-700 font-medium text-sm mb-4 inline-block">
                ← Back to Consultants
              </Link>
              <h1 className="text-3xl md:text-4xl font-bold mb-2">
                <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  Book an Appointment
                </span>
              </h1>
              <p className="text-gray-600">Schedule your session with {consultant.name}</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Consultant Info Card */}
              <div className="lg:col-span-1">
                <div className="bg-white rounded-2xl shadow-lg p-6 sticky top-4">
                  <div className="bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl p-6 mb-4">
                    <div className="w-20 h-20 rounded-full bg-white/20 backdrop-blur-sm border-4 border-white mx-auto flex items-center justify-center text-2xl font-bold text-white mb-3">
                      {consultant.image}
                    </div>
                    <h3 className="text-xl font-bold text-white text-center">{consultant.name}</h3>
                    <p className="text-blue-100 text-center text-sm">{consultant.specialty}</p>
                  </div>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between items-center py-2 border-b">
                      <span className="text-gray-600">Session Fee</span>
                      <span className="font-bold text-gray-900">${consultant.price}/hour</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b">
                      <span className="text-gray-600">Duration</span>
                      <span className="font-bold text-gray-900">60 minutes</span>
                    </div>
                    <div className="flex justify-between items-center py-2">
                      <span className="text-gray-600">Response Time</span>
                      <span className="font-bold text-gray-900">Within 24h</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Booking Form */}
              <div className="lg:col-span-2">
                <div className="bg-white rounded-2xl shadow-lg p-6 md:p-8 space-y-8">
                  {/* Appointment Type */}
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 mb-4">Appointment Type</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <button
                        onClick={() => setAppointmentType("video")}
                        className={`p-4 rounded-xl border-2 transition-all ${
                          appointmentType === "video"
                            ? "border-blue-600 bg-blue-50"
                            : "border-gray-200 hover:border-blue-300"
                        }`}
                      >
                        <div className="text-3xl mb-2">📹</div>
                        <div className="font-semibold text-gray-900">Video Call</div>
                        <div className="text-xs text-gray-600">Online session</div>
                      </button>
                      <button
                        onClick={() => setAppointmentType("phone")}
                        className={`p-4 rounded-xl border-2 transition-all ${
                          appointmentType === "phone"
                            ? "border-blue-600 bg-blue-50"
                            : "border-gray-200 hover:border-blue-300"
                        }`}
                      >
                        <div className="text-3xl mb-2">📞</div>
                        <div className="font-semibold text-gray-900">Phone Call</div>
                        <div className="text-xs text-gray-600">Voice only</div>
                      </button>
                    </div>
                  </div>

                  {/* Date Selection */}
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 mb-4">Select Date</h3>
                    <div className="grid grid-cols-7 gap-2">
                      {availableDays.map((day) => (
                        <button
                          key={day.date}
                          onClick={() => setSelectedDate(day.date)}
                          className={`p-3 rounded-xl border-2 transition-all text-center ${
                            selectedDate === day.date
                              ? "border-blue-600 bg-blue-50"
                              : "border-gray-200 hover:border-blue-300"
                          }`}
                        >
                          <div className="text-xs text-gray-600 mb-1">{day.day}</div>
                          <div className="font-bold text-gray-900">{day.dayNum}</div>
                          <div className="text-xs text-gray-500">{day.month}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Time Selection */}
                  {selectedDate && (
                    <div>
                      <h3 className="text-lg font-bold text-gray-900 mb-4">Select Time</h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {timeSlots.map((slot) => (
                          <button
                            key={slot.time}
                            onClick={() => slot.available && setSelectedTime(slot.time)}
                            disabled={!slot.available}
                            className={`p-3 rounded-lg border-2 font-medium transition-all ${
                              selectedTime === slot.time
                                ? "border-blue-600 bg-blue-50 text-blue-700"
                                : slot.available
                                ? "border-gray-200 hover:border-blue-300 text-gray-900"
                                : "border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed"
                            }`}
                          >
                            {slot.time}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 mb-4">Additional Notes (Optional)</h3>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Let the consultant know about your health concerns or questions..."
                      rows={4}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-600 focus:outline-none transition-colors"
                    />
                  </div>

                  {/* Booking Summary */}
                  {selectedDate && selectedTime && (
                    <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 border-l-4 border-blue-600">
                      <h4 className="font-bold text-gray-900 mb-3">Appointment Summary</h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">Date:</span>
                          <span className="font-semibold text-gray-900">
                            {new Date(selectedDate).toLocaleDateString('en-US', { 
                              weekday: 'long', 
                              year: 'numeric', 
                              month: 'long', 
                              day: 'numeric' 
                            })}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Time:</span>
                          <span className="font-semibold text-gray-900">{selectedTime}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Type:</span>
                          <span className="font-semibold text-gray-900">{appointmentType === "video" ? "Video Call" : "Phone Call"}</span>
                        </div>
                        <div className="flex justify-between pt-2 border-t border-blue-200">
                          <span className="text-gray-600">Total:</span>
                          <span className="font-bold text-blue-700 text-lg">${consultant.price}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Book Button */}
                  <button
                    onClick={handleBookAppointment}
                    disabled={!selectedDate || !selectedTime}
                    className={`w-full py-4 rounded-xl font-bold text-lg transition-all ${
                      selectedDate && selectedTime
                        ? "bg-gradient-to-r from-blue-600 to-blue-700 text-white hover:shadow-2xl hover:scale-105"
                        : "bg-gray-200 text-gray-400 cursor-not-allowed"
                    }`}
                  >
                    Confirm Appointment
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
      ) : (
        <section className="flex-1 flex items-center justify-center px-4 py-16">
          <div className="max-w-md w-full">
            <div className="bg-white rounded-2xl shadow-2xl p-8 text-center">
              <div className="w-20 h-20 bg-gradient-to-r from-green-400 to-green-600 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Appointment Confirmed!</h2>
              <p className="text-gray-600 mb-6">Your appointment has been successfully booked.</p>
              
              <div className="bg-gray-50 rounded-xl p-4 mb-6 text-left space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Consultant:</span>
                  <span className="font-semibold">{consultant.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Date:</span>
                  <span className="font-semibold">
                    {new Date(selectedDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Time:</span>
                  <span className="font-semibold">{selectedTime}</span>
                </div>
              </div>

              <p className="text-sm text-gray-600 mb-6">
                A confirmation email has been sent to your registered email address with meeting details.
              </p>

              <div className="space-y-3">
                <Link
                  href="/profile"
                  className="block w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white py-3 rounded-lg font-semibold hover:shadow-lg transition-all"
                >
                  View My Appointments
                </Link>
                <Link
                  href="/consultants"
                  className="block w-full border-2 border-gray-300 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-all"
                >
                  Book Another Appointment
                </Link>
              </div>
            </div>
          </div>
        </section>
      )}

      <footer className="py-6 text-center text-sm text-gray-500 border-t border-gray-200 bg-white/50 backdrop-blur-sm">
        <p>© {new Date().getFullYear()} Health Hive. All rights reserved.</p>
      </footer>
    </main>
  );
}