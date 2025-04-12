import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import io from "socket.io-client";

const socket = io("https://0110-103-48-101-59.ngrok-free.app", { transports: ["websocket"] });  // Matches backend Ngrok URL

const Borrower = ({ borrowers }) => {
  const { phone } = useParams();
  const navigate = useNavigate();
  const borrower = borrowers.find((b) => String(b.Mobile_No) === phone) || {};
  const [campaignStatus, setCampaignStatus] = useState({});
  const [callAttempts, setCallAttempts] = useState(0);
  const [messageAttempts, setMessageAttempts] = useState(0);
  const [callStatus, setCallStatus] = useState({});
  const [whatsappStatus, setWhatsappStatus] = useState("Not Initiated");
  const [whatsappMessage, setWhatsappMessage] = useState("");

  const BACKEND_URL = "https://0110-103-48-101-59.ngrok-free.app";  // Local dev; use Ngrok URL in production (e.g., "https://adbe-103-48-103-198.ngrok-free.app")

  const fetchAttempts = () => {
    fetch(`${BACKEND_URL}/get-attempts/${phone}`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        return res.json();
      })
      .then(data => {
        setCallAttempts(data.voice_attempts);
        setMessageAttempts(data.message_attempts);
        console.log(`Fetched attempts for ${phone}: voice=${data.voice_attempts}, message=${data.message_attempts}`);
      })
      .catch(err => console.error("Failed to fetch attempts:", err));
  };

  useEffect(() => {
    fetchAttempts();

    socket.on("connect", () => console.log("Socket connected"));
    socket.on("call_status", (data) => {
      console.log("Call status received:", data);
      if (data.phone === phone) {
        setCallStatus((prev) => ({ ...prev, [data.phone]: data.status }));
        fetchAttempts();
      }
    });
    socket.on("whatsapp_status", (data) => {
      console.log("WhatsApp status received:", data);
      if (data.phone === phone) {
        setWhatsappStatus(data.status);
        if (data.message) setWhatsappMessage(data.message);
        fetchAttempts();
      }
    });
    socket.on("campaign_status", (data) => {
      console.log("Campaign status received:", data);
      if (data.phone === phone) {
        setCampaignStatus((prev) => ({ ...prev, [data.phone]: data.status }));
      }
    });

    return () => {
      socket.off("connect");
      socket.off("call_status");
      socket.off("whatsapp_status");
      socket.off("campaign_status");
    };
  }, [phone]);

  const startCampaign = () => {
    if (!borrower.Mobile_No) return;
    setCampaignStatus((prev) => ({ ...prev, [borrower.Mobile_No]: "Running" }));
    socket.emit("start_campaign", { borrowers: [borrower] });
  };

  if (!borrower.Mobile_No) {
    return (
      <div className="min-h-screen p-6 bg-gradient-to-br from-blue-50 to-indigo-100 font-sans text-gray-800">
        <header className="bg-white p-6 rounded-lg shadow-md border-l-4 border-blue-600 mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-blue-600">Borrower Not Found</h1>
          <button onClick={() => navigate("/")} className="text-blue-500 hover:underline text-lg">
            Back to List
          </button>
        </header>
        <p className="text-gray-500 text-center">No borrower found for phone: {phone}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 bg-gradient-to-br from-blue-50 to-indigo-100 font-sans text-gray-800">
      <header className="bg-white p-6 rounded-lg shadow-md border-l-4 border-blue-600 mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-blue-600">
            {borrower.F_Name} {borrower.L_Name}
          </h1>
          <p className="text-sm text-gray-500">Borrower Details & Communication</p>
        </div>
        <button onClick={() => navigate("/")} className="text-blue-500 hover:underline text-lg">
          Back to List
        </button>
      </header>
      <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-indigo-500 mb-6">
        <h3 className="text-lg font-semibold text-indigo-500 mb-4">Details</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <p><strong>Phone:</strong> {borrower.Mobile_No}</p>
          <p><strong>Channel Preference:</strong> {borrower.Channel_Preference || "N/A"}</p>
          <p><strong>Balance:</strong> Rs. {borrower.Current_balance || "N/A"}</p>
          <p><strong>Due Date:</strong> {borrower.Date_of_last_payment || "N/A"}</p>
        </div>
        <button
          onClick={startCampaign}
          className="mt-6 w-full py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
        >
          Start Campaign
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-blue-500">
          <h3 className="text-lg font-semibold text-blue-500 mb-3">Voice Communication</h3>
          <p className="text-sm">
            <strong>Status:</strong> {callStatus[borrower.Mobile_No] || "Not Initiated"}
          </p>
          <p className="text-sm">
            <strong>Unanswered Attempts:</strong> {callAttempts}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-teal-500">
          <h3 className="text-lg font-semibold text-teal-500 mb-3">WhatsApp Communication</h3>
          <p className="text-sm">
            <strong>Status:</strong> {whatsappStatus}
          </p>
          <p className="text-sm">
            <strong>Message:</strong> {whatsappMessage || "N/A"}
          </p>
          <p className="text-sm">
            <strong>Unresponded Attempts:</strong> {messageAttempts}
          </p>
        </div>
      </div>
    </div>
  );
};

export default Borrower;