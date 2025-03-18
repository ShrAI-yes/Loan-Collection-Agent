// Add ngrok url given to you in the socket connection placeholder 'ngrok_url'

import React, { useState, useEffect } from "react";
import io from "socket.io-client";
import { Bar } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from "chart.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const socket = io("your_ngrok_url", { transports: ["websocket"] });   //e.g., "https://abcd1234.ngrok.io"

const App = () => {
  const [borrowers, setBorrowers] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [selectedBorrower, setSelectedBorrower] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("en");
  const [conversation, setConversation] = useState([]);
  const [callStatus, setCallStatus] = useState(null);
  const [callLogs, setCallLogs] = useState([]);
  const [showLatencyChart, setShowLatencyChart] = useState(false);

  useEffect(() => {
    fetch("/borrowers.json").then((res) => res.json()).then((data) => setBorrowers(data));
    fetch("/languages.json").then((res) => res.json()).then((data) => setLanguages(data));

    socket.on("connect", () => console.log("Socket connected"));

    socket.on("call_status", (data) => {
      setCallStatus(data.status);
      setCallLogs((prevLogs) => {
        if (data.status === "completed") setShowLatencyChart(true); // Show chart when call ends
        if (data.status === "initiated" && prevLogs.some(log => log.call_sid === data.call_sid)) return prevLogs;
        return [...prevLogs, { call_sid: data.call_sid || "unknown", status: data.status }];
      });
    });

    socket.on("conversation_update", (data) => {
      console.log("Conversation update received:", data); // Debug incoming data
      if (data.user) {
        setConversation((prev) => [...prev, {
          sender: "User",
          text: data.user,
          latency_breakdown: data.latency_breakdown || {} // Fallback to empty object
        }]);
      }
      if (data.bot) {
        setConversation((prev) => [...prev, {
          sender: "Bot",
          text: data.bot,
          latency_breakdown: data.latency_breakdown || {} // Fallback to empty object
        }]);
      }
    });

    socket.on("error", (error) => setCallStatus("Error: " + (error.message || "Unknown error")));

    return () => {
      socket.off("connect");
      socket.off("call_status");
      socket.off("conversation_update");
      socket.off("error");
    };
  }, []);

  const startCall = async () => {
    if (!selectedBorrower) {
      alert("Please select a borrower before starting a call.");
      return;
    }
    setCallStatus("Initiating call...");
    setConversation([]);
    setShowLatencyChart(false);
    //mapping the language name to code before sending
    const languageCode = languages.find(lang => lang.name === selectedLanguage)?.code || "en";
    socket.emit("start_call", { phone: selectedBorrower, language: languageCode });
  };

  const getAverageLatencies = () => {
    const components = ["platform", "voice", "llm", "transcription", "telephony"];
    const totals = { platform: 0, voice: 0, llm: 0, transcription: 0, telephony: 0 };
    let validCount = 0;
  
    conversation.forEach((msg) => {
      if (msg.latency_breakdown && typeof msg.latency_breakdown === "object") {
        validCount++;
        components.forEach((comp) => {
          totals[comp] += msg.latency_breakdown[comp] || 0;
        });
      }
    });


    return components.map((comp) => ({
      component: comp.charAt(0).toUpperCase() + comp.slice(1), // Capitalize for display
      average: validCount > 0 ? (totals[comp] / validCount) : 0 // Keep as raw numbers for precision
    }));
  };

  const chartData = {
    labels: getAverageLatencies().map((item) => item.component),
    datasets: [{
      label: "Average Latency (s)",
      data: getAverageLatencies().map((item) => item.average),
      backgroundColor: [
        "rgba(255, 99, 132, 0.8)",  // Red for platform
        "rgba(54, 162, 235, 0.8)",  // Blue for voice
        "rgba(255, 206, 86, 0.8)",  // Yellow for llm
        "rgba(75, 192, 192, 0.8)",  // Teal for transcription
        "rgba(153, 102, 255, 0.8)"  // Purple for telephony
      ],
      borderColor: [
        "rgba(255, 99, 132, 1)",
        "rgba(54, 162, 235, 1)",
        "rgba(255, 206, 86, 1)",
        "rgba(75, 192, 192, 1)",
        "rgba(153, 102, 255, 1)"
      ],
      borderWidth: 2,
    }]
  };

  return (
    <div className="w-full min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center">
      <div className="max-w-3xl w-full p-6 bg-gray-800 rounded-lg shadow-lg">
        <h2 className="text-3xl font-bold mb-6 text-blue-400 text-center">Conversational AI</h2>

        {/* Borrower and Language Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium mb-1">Borrower:</label>
          <select className="w-full p-3 border border-gray-600 rounded bg-gray-700 text-white"
            onChange={(e) => setSelectedBorrower(e.target.value)} value={selectedBorrower}>
            <option value="">Select Borrower</option>
            {borrowers.map((b) => <option key={b.phone} value={b.phone}>{b.name} ({b.phone})</option>)}
          </select>
        </div>
        <div className="mb-6">
          <label className="block text-sm font-medium mb-1">Language:</label>
          <select className="w-full p-3 border border-gray-600 rounded bg-gray-700 text-white"
            onChange={(e) => setSelectedLanguage(e.target.value)} value={selectedLanguage}>
            {languages.map((lang) => <option key={lang.code} value={lang.name}>{lang.name}</option>)}
          </select>
        </div>

        <button className="w-full p-3 bg-blue-500 rounded hover:bg-blue-600 transition duration-300 mb-6" onClick={startCall}>
          Start Call
        </button>

        {callStatus && <p className="text-yellow-400 text-center mb-6">Status: {callStatus}</p>}

        {/* Conversation Display */}
        <h3 className="text-xl font-semibold mb-2">Conversation</h3>
        <div className="w-full bg-gray-700 p-4 rounded h-40 overflow-y-auto">
          {conversation.length === 0 ? (
            <p className="text-gray-400 italic">No conversation yet</p>
          ) : (
            conversation.map((msg, index) => (
              <p key={index} className="text-sm mb-1">
                <strong className={msg.sender === "User" ? "text-green-400" : "text-blue-400"}>
                  {msg.sender}:
                </strong> {msg.text}{" "}
                {msg.latency_breakdown && (
                  <small className="text-gray-400">
                    (Platform: {(msg.latency_breakdown.platform || 0).toFixed(7)}s, 
                    Voice: {(msg.latency_breakdown.voice || 0).toFixed(7)}s, 
                    LLM: {(msg.latency_breakdown.llm || 0).toFixed(7)}s, 
                    Transcription: {(msg.latency_breakdown.transcription || 0).toFixed(7)}s, 
                    Telephony: {(msg.latency_breakdown.telephony || 0).toFixed(7)}s)
                  </small>
                )}
              </p>
            ))
          )}
        </div>

        {/* Call Logs */}
        <h3 className="text-xl font-semibold mt-6 mb-2">Call Logs</h3>
        <ul className="w-full bg-gray-700 p-4 rounded h-32 overflow-y-auto">
          {callLogs.length === 0 ? (
            <li className="text-gray-400 italic">No call logs yet</li>
          ) : (
            callLogs.map((log, index) => (
              <li key={index} className="text-sm text-gray-300 mb-1">Call {log.call_sid}: {log.status}</li>
            ))
          )}
        </ul>

        {showLatencyChart && (
        <div className="mt-6 bg-gray-700 p-4 rounded-lg shadow-md">
          <h3 className="text-xl font-semibold mb-4 text-white">Average Latency Distribution</h3>
          <Bar
            data={chartData}
            options={{
              indexAxis: "y", // Makes it a horizontal bar chart
              responsive: true,
              plugins: {
                legend: {
                  position: "top",
                  labels: {
                    color: "#ffffff",
                    font: { size: 14 }
                  }
                },
                title: {
                  display: true,
                  text: "Average Latency per Component (seconds)",
                  color: "#ffffff",
                  font: { size: 16, weight: "bold" }
                },
                tooltip: {
                  callbacks: {
                    label: (context) => `${context.raw.toFixed(3)}s` // Show 3 decimal places in tooltips
                  }
                }
              },
              scales: {
                x: {
                  title: {
                    display: true,
                    text: "Latency (seconds)",
                    color: "#ffffff",
                    font: { size: 14 }
                  },
                  ticks: {
                    color: "#ffffff",
                    precision: 3 // Show 3 decimal places on axis
                  },
                  grid: {
                    color: "rgba(255, 255, 255, 0.1)"
                  }
                },
                y: {
                  title: {
                    display: true,
                    text: "Components",
                    color: "#ffffff",
                    font: { size: 14 }
                  },
                  ticks: {
                    color: "#ffffff",
                    font: { size: 12 }
                  },
                  grid: {
                    display: false // Cleaner look
                  }
                }
              }
            }}
          />
        </div>
      )}
    </div>
  </div>
);
};

export default App;