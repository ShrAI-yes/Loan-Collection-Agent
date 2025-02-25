import React from "react"; 
import { useState, useEffect } from "react";
import io from "socket.io-client";

const socket = io("YOUR_NGROK_URL", { transports: ["websocket"] });

const App = () => {
  const [borrowers, setBorrowers] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [selectedBorrower, setSelectedBorrower] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("English");
  const [conversation, setConversation] = useState([]);
  const [callStatus, setCallStatus] = useState(null);
  const [callLogs, setCallLogs] = useState([]);
  
  useEffect(() => {
    fetch("/borrowers.json")
      .then((res) => res.json())
      .then((data) => setBorrowers(data))
      .catch((err) => console.error("Error loading borrowers: ", err));

    fetch("/languages.json")
      .then((res) => res.json())
      .then((data) => setLanguages(data))
      .catch((err) => console.error("Error loading languages: ", err));

    socket.on("connect", () => {
      console.log("Socket connected");
    });

    socket.on("call_status", (data) => {
      console.log("Call status update:", data);
      setCallStatus(data.status);
      setCallLogs((prevLogs) => {
        if (data.status === "initiated" && prevLogs.some(log => log.call_sid === data.call_sid && log.status === "initiated")) {
          return prevLogs; 
        }
      return [...prevLogs, { call_sid: data.call_sid || "unknown", status: data.status }];
    });
  });
  
    socket.on("conversation_update", (data) => {
      console.log("Conversation update:", data);
      if (data.user) {
        setConversation((prev) => [...prev, {
          sender: "User",
          text: data.user,
          latency: data.latency?.toFixed(2) || 0
        }]);
      } 
      
      if (data.bot) {
        setConversation((prev) => [...prev, {
          sender: "Bot",
          text: data.bot,
          latency: data.latency?.toFixed(2) || 0
        }]);
      }
    });

    socket.on("error", (error) => {
      console.error("Socket error:", error);
      setCallStatus("Error: " + (error.message || "Unknown error"));
    });
  
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
    
    // setCallStatus("Initiating call...");
    setConversation([]); 
    
    socket.emit("start_call", {
      phone: selectedBorrower,
      language: selectedLanguage
    });
    
    console.log("Call request sent for:", selectedBorrower);
  };

  return (
    <div className="w-full min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center">
      <div className="max-w-3xl w-full p-6 bg-gray-800 rounded-lg shadow-lg">
        <h2 className="text-3xl font-bold mb-6 text-blue-400 text-center">Conversational AI</h2>
  
        <div className="mb-6">
          <label className="block text-sm font-medium mb-1">Borrower:</label>
          <select
            className="w-full p-3 border border-gray-600 rounded bg-gray-700 text-white"
            onChange={(e) => setSelectedBorrower(e.target.value)}
            value={selectedBorrower}
          >
            <option value="">Select Borrower</option>
            {borrowers.map((b) => (
              <option key={b.phone} value={b.phone}>{b.name} ({b.phone})</option>
            ))}
          </select>
        </div>
  
        <div className="mb-6">
          <label className="block text-sm font-medium mb-1">Language:</label>
          <select
            className="w-full p-3 border border-gray-600 rounded bg-gray-700 text-white"
            onChange={(e) => setSelectedLanguage(e.target.value)}
            value={selectedLanguage}
          >
            {languages.map((lang) => (
              <option key={lang.code} value={lang.name}>{lang.name}</option>
            ))}
          </select>
        </div>
  
        <button 
          className="w-full p-3 bg-blue-500 rounded hover:bg-blue-600 transition duration-300 mb-6"
          onClick={startCall}
        >
          Start Call
        </button>
  
        {callStatus && <p className="text-yellow-400 text-center mb-6">Status: {callStatus}</p>}
  
        <h3 className="text-xl font-semibold mb-2">Conversation</h3>
        <div className="w-full bg-gray-700 p-4 rounded h-40 overflow-y-auto">
          {conversation.length === 0 ? (
            <p className="text-gray-400 italic">No conversation yet</p>
          ) : (
            conversation.map((msg, index) => (
              <p key={index} className="text-sm mb-1">
                <strong className={msg.sender === "User" ? "text-green-400" : "text-blue-400"}>
                  {msg.sender}:
                </strong> {msg.text} <small className="text-gray-400">({msg.latency}s)</small>
              </p>
            ))
          )}
        </div>
  
        <h3 className="text-xl font-semibold mt-6 mb-2">Call Logs</h3>
        <ul className="w-full bg-gray-700 p-4 rounded h-32 overflow-y-auto">
          {callLogs.length === 0 ? (
            <li className="text-gray-400 italic">No call logs yet</li>
          ) : (
            callLogs.map((log, index) => (
              <li key={index} className="text-sm text-gray-300 mb-1">
                Call {log.call_sid}: {log.status}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );  
};

export default App;


