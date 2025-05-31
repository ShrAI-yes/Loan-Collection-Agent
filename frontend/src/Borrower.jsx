import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import io from "socket.io-client";

const BACKEND_URL = "http://localhost:5000";
const SOCKET_URL = "https://fdf5-103-185-11-75.ngrok-free.app";

const socket = io(SOCKET_URL, {
  transports: ["websocket"],
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
});

const Borrower = ({ borrowers }) => {
  const { phone } = useParams();
  const navigate = useNavigate();
  const borrower = borrowers.find((b) => String(b.Mobile_No) === phone) || {};
  const [campaignStatus, setCampaignStatus] = useState("Not Started");
  const [callAttempts, setCallAttempts] = useState(0);
  const [messageAttempts, setMessageAttempts] = useState(0);
  const [callStatus, setCallStatus] = useState("Not Initiated");
  const [whatsappStatus, setWhatsappStatus] = useState("Not Initiated");
  const [voiceMessages, setVoiceMessages] = useState([]);
  const [whatsappMessages, setWhatsappMessages] = useState([]);
  const [debugInfo, setDebugInfo] = useState("");

  const fetchAttempts = async () => {
    try {
      console.log(`Fetching attempts from ${BACKEND_URL}/get-attempts/${phone}`);
      const res = await fetch(`${BACKEND_URL}/get-attempts/${phone}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        throw new Error(`HTTP error! Status: ${res.status}, Text: ${await res.text()}`);
      }
      const data = await res.json();
      setCallAttempts(data.voice_attempts || 0);
      setMessageAttempts(data.message_attempts || 0);
      console.log(`Fetched attempts for ${phone}: voice=${data.voice_attempts}, message=${data.message_attempts}`);
      setDebugInfo(`Last fetch: voice=${data.voice_attempts}, message=${data.message_attempts}`);
    } catch (err) {
      console.error("Failed to fetch attempts:", err);
      setDebugInfo(`Fetch error: ${err.message}`);
    }
  };

  useEffect(() => {
    fetchAttempts();

    socket.on("connect", () => {
      console.log("Socket connected");
      setDebugInfo("Socket connected");
    });

    socket.on("connect_error", (err) => {
      console.error("Socket connection error:", err);
      setDebugInfo(`Socket error: ${err.message}`);
    });

    socket.on("call_status", (data) => {
      console.log("Call status received:", data);
      if (data.phone === phone) {
        setCallStatus(data.status);
        fetchAttempts();
        setDebugInfo(`Call status: ${data.status}`);
      }
    });

    socket.on("whatsapp_status", (data) => {
      console.log("WhatsApp status received:", data);
      if (data.phone === phone) {
        setWhatsappStatus(data.status);
        if (data.sender && data.message) {
          console.log(`Adding WhatsApp message: sender=${data.sender}, text=${data.message}`);
          setWhatsappMessages((prev) => [
            ...prev,
            {
              sender: data.sender,
              text: data.message,
              time: new Date().toLocaleTimeString(),
            },
          ]);
        } else {
          console.warn("Skipping WhatsApp message due to missing fields:", {
            phone: data.phone,
            status: data.status,
            sender: data.sender,
            message: data.message,
          });
        }
        fetchAttempts();
        setDebugInfo(`WhatsApp status: ${data.status}, message: ${data.message || "N/A"}`);
      }
    });

    socket.on("conversation_update", (data) => {
      console.log("Conversation update received:", data);
      if (data.phone === phone && data.sender && data.text) {
        console.log(`Adding voice message: sender=${data.sender}, text=${data.text}`);
        setVoiceMessages((prev) => [
          ...prev,
          {
            sender: data.sender,
            text: data.text,
            time: new Date().toLocaleTimeString(),
          },
        ]);
      } else {
        console.warn("Skipping voice message due to missing fields:", {
          phone: data.phone,
          sender: data.sender,
          text: data.text,
        });
      }
    });

    socket.on("campaign_status", (data) => {
      console.log("Campaign status received:", data);
      if (data.phone === phone) {
        setCampaignStatus(data.status);
        setDebugInfo(`Campaign status: ${data.status}`);
      }
    });

    return () => {
      socket.off("connect");
      socket.off("connect_error");
      socket.off("call_status");
      socket.off("whatsapp_status");
      socket.off("conversation_update");
      socket.off("campaign_status");
    };
  }, [phone]);

  const startCampaign = () => {
    if (!borrower.Mobile_No) return;
    setCampaignStatus("Running");
    socket.emit("start_campaign", { borrowers: [borrower] });
    setDebugInfo("Campaign started");
  };

  if (!borrower.Mobile_No) {
    return (
      <div className="min-h-screen p-6 bg-gray-100 font-sans">
        <header className="bg-white p-6 rounded-lg shadow-md mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-blue-600">Borrower Not Found</h1>
          <button
            onClick={() => navigate("/")}
            className="text-blue-500 hover:underline text-lg"
          >
            Back to List
          </button>
        </header>
        <p className="text-gray-500 text-center">No borrower found for phone: {phone}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 bg-gray-100 font-sans">
      <header className="bg-white p-6 rounded-lg shadow-md mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-blue-600">
            {borrower.F_Name} {borrower.L_Name}
          </h1>
          <p className="text-sm text-gray-500">Borrower Details & Communication</p>
        </div>
        <button
          onClick={() => navigate("/")}
          className="text-blue-500 hover:underline text-lg"
        >
          Back to List
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Details & Campaign */}
        <div className="lg:col-span-1">
          <div className="bg-white p-6 rounded-lg shadow-md mb-6">
            <h3 className="text-lg font-semibold text-blue-600 mb-4">Details</h3>
            <div className="space-y-2 text-sm">
              <p><strong>Phone:</strong> {borrower.Mobile_No}</p>
              <p><strong>Channel:</strong> {borrower.Channel_Preference || "N/A"}</p>
              <p><strong>Balance:</strong> Rs. {borrower.Current_balance || "N/A"}</p>
              <p><strong>Due Date:</strong> {borrower.Date_of_last_payment || "N/A"}</p>
            </div>
            <button
              onClick={startCampaign}
              className="mt-4 w-full py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
            >
              Start Campaign
            </button>
            <p className="mt-2 text-sm text-gray-500">Status: {campaignStatus}</p>
          </div>
        </div>

        {/* Voice & WhatsApp Communication */}
        <div className="lg:col-span-2">
          {/* Voice Conversation */}
          <div className="bg-white p-6 rounded-lg shadow-md mb-6">
            <h3 className="text-lg font-semibold text-blue-600 mb-4">Voice Conversation</h3>
            <p className="text-sm mb-2"><strong>Status:</strong> {callStatus}</p>
            <p className="text-sm mb-2"><strong>Attempts:</strong> {callAttempts}</p>
            <div className="max-h-96 overflow-y-auto p-4 bg-gray-50 rounded-lg">
              {voiceMessages.length > 0 ? (
                voiceMessages.map((msg, index) => (
                  <div
                    key={`voice-${index}`}
                    className={`mb-4 flex ${
                      msg.sender === "User" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-xs p-3 rounded-lg shadow-sm ${
                        msg.sender === "User"
                          ? "bg-blue-500 text-white"
                          : "bg-gray-200 text-gray-800"
                      }`}
                    >
                      <p className="text-sm font-semibold">{msg.sender}</p>
                      <p>{msg.text}</p>
                      <p className="text-xs mt-1 opacity-70">{msg.time}</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">No voice messages yet</p>
              )}
            </div>
          </div>

          {/* WhatsApp Conversation */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-lg font-semibold text-blue-600 mb-4">WhatsApp Conversation</h3>
            <p className="text-sm mb-2"><strong>Status:</strong> {whatsappStatus}</p>
            <p className="text-sm mb-2"><strong>Attempts:</strong> {messageAttempts}</p>
            <div className="max-h-96 overflow-y-auto p-4 bg-gray-50 rounded-lg">
              {whatsappMessages.length > 0 ? (
                whatsappMessages.map((msg, index) => (
                  <div
                    key={`whatsapp-${index}`}
                    className={`mb-4 flex ${
                      msg.sender === "User" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-xs p-3 rounded-lg shadow-sm ${
                        msg.sender === "User"
                          ? "bg-blue-500 text-white"
                          : "bg-gray-200 text-gray-800"
                      }`}
                    >
                      <p className="text-sm font-semibold">{msg.sender}</p>
                      <p>{msg.text}</p>
                      <p className="text-xs mt-1 opacity-70">{msg.time}</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">No WhatsApp messages yet</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Borrower;