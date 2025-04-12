
import React, { useState, useEffect } from "react";
import { Routes, Route, Link } from "react-router-dom";
import io from "socket.io-client";
import Borrower from "./Borrower.jsx";

const socket = io("https://0110-103-48-101-59.ngrok-free.app", { transports: ["websocket"] });

const App = () => {
  const [file, setFile] = useState(null);
  const [borrowers, setBorrowers] = useState([]);

  useEffect(() => {
    socket.on("connect", () => console.log("Socket connected"));
    socket.on("connect_error", (err) => console.error("Socket error:", err));
    socket.on("borrowers_update", (data) => {
      setBorrowers(data.borrowers);
    });

    return () => {
      socket.off("connect");
      socket.off("connect_error");
      socket.off("borrowers_update");
    };
  }, []);

  const handleFileUpload = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    setFile(selectedFile);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("https://0110-103-48-101-59.ngrok-free.app/upload-csv", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Upload failed");
      const data = await response.json();
      setBorrowers(data.borrowers);
    } catch (err) {
      console.error("Upload error:", err);
      alert("Failed to upload CSV");
    }
  };

  return (
    <Routes>
      <Route
        path="/"
        element={
          <div className="min-h-screen p-6 bg-gradient-to-br from-blue-50 to-indigo-100 font-sans text-gray-800">
            {/* Header */}
            <header className="bg-white p-6 rounded-lg shadow-md border-l-4 border-blue-600 mb-6 text-center">
              <h1 className="text-2xl font-bold text-blue-600">Conversational AI Portal</h1>
              <p className="text-sm text-gray-500">Efficient Borrower Communication</p>
            </header>

            {/* Upload Section */}
            <div className="bg-white p-4 rounded-lg shadow-md border-l-4 border-green-500 mb-6">
              <h3 className="text-lg font-semibold text-green-500 mb-3">Upload Borrowers</h3>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="w-full p-2 border rounded-md bg-gray-50"
              />
              {file && (
                <p className="mt-2 text-sm text-green-500">
                  {file.name}{" "}
                  <button onClick={() => setFile(null)} className="text-red-500 hover:underline">
                    Remove
                  </button>
                </p>
              )}
            </div>

            {/* Borrowers Table */}
            <div className="bg-white p-4 rounded-lg shadow-md border-l-4 border-indigo-500">
              <h3 className="text-lg font-semibold text-indigo-500 mb-3">Borrowers</h3>
              {borrowers.length === 0 ? (
                <p className="text-gray-500 text-center">No borrowers loaded yet</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="p-2">Name</th>
                        <th className="p-2">Phone</th>
                        <th className="p-2">Channel Preference</th>
                      </tr>
                    </thead>
                    <tbody>
                      {borrowers.map((b) => (
                        <tr key={b.Mobile_No} className="border-t hover:bg-gray-50 cursor-pointer">
                          <td className="p-2">
                            <Link
                              to={`/borrower/${b.Mobile_No}`}
                              className="text-blue-500 hover:underline"
                            >
                              {b.F_Name} {b.L_Name}
                            </Link>
                          </td>
                          <td className="p-2">{b.Mobile_No}</td>
                          <td className="p-2">{b.Channel_Preference}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        }
      />
      <Route path="/borrower/:phone" element={<Borrower borrowers={borrowers} />} />
    </Routes>
  );
};

export default App;