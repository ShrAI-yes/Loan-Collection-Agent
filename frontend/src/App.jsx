// import React, { useState, useEffect } from "react";

// export default function App() {
//   const [messages, setMessages] = useState([]);
//   const [listening, setListening] = useState(false);
//   const [userInput, setUserInput] = useState("");
//   const [latency, setLatency] = useState(null);
//   const [logLink, setLogLink] = useState(null);

//   useEffect(() => {
//     if (!("webkitSpeechRecognition" in window)) {
//       console.warn("Speech recognition not supported in this browser.");
//       return;
//     }

//     let recognition = new webkitSpeechRecognition();
//     recognition.continuous = false;
//     recognition.lang = "en-US";

//     recognition.onstart = () => setListening(true);
//     recognition.onend = () => setListening(false);
//     recognition.onresult = (event) => {
//       const transcript = event.results[0][0].transcript;
//       handleUserInput(transcript);
//     };

//     if (listening) {
//       recognition.start();
//     }

//     return () => {
//       recognition.onend = null;
//       recognition.stop();
//     };
//   }, [listening]);

//   const handleUserInput = async (text) => {
//     if (!text || text.trim() === "") return;

//     setMessages((prev) => [...prev, { sender: "You", text }]);
//     setUserInput("");

//     const startTime = performance.now();
//     try {
//       const response = await fetch("http://127.0.0.1:5000/chat", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ message: text }),
//       });

//       const endTime = performance.now();
//       setLatency((endTime - startTime).toFixed(2) + " ms");

//       if (!response.ok) throw new Error("Failed to fetch response");

//       const data = await response.json();
//       setMessages((prev) => [...prev, { sender: "Bot", text: data.response }]);
//       if (data.log_url) setLogLink(data.log_url);
//     } catch (error) {
//       console.error("Error fetching response:", error);
//     }
//   };

//   return (
//     <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white p-4">
//       <h1 className="text-3xl font-bold mb-4 text-neon-blue">Loan Voice Assistant</h1>
//       <div className="w-full max-w-md bg-gray-800 shadow-lg rounded-lg p-4 h-96 overflow-y-auto border border-neon-blue">
//         {messages.map((msg, index) => (
//           <p
//             key={index}
//             className={`p-2 ${msg.sender === "You" ? "text-pink" : "text-green"}`}
//           >
//             <strong>{msg.sender}:</strong> {msg.text}
//           </p>
//         ))}
//       </div>
//       <div className="mt-2 text-neon-yellow">
//         {latency && <p>Response Time: {latency}</p>}
//         {logLink && (
//           <p>
//             <a href={logLink} target="_blank" rel="noopener noreferrer" className="underline">
//               View Call Log
//             </a>
//           </p>
//         )}
//       </div>
//       <div className="flex w-full max-w-md mt-4">
//         <input
//           type="text"
//           className="flex-1 p-2 border border-neon-blue bg-gray-700 text-white rounded-l focus:outline-none"
//           value={userInput}
//           onChange={(e) => setUserInput(e.target.value)}
//           placeholder="Type a message..."
//         />
//         <button
//           onClick={() => handleUserInput(userInput)}
//           className="bg-neon-blue text-white p-2"
//         >
//           Send
//         </button>
//         <button
//           onClick={() => setListening(true)}
//           className={`p-2 ml-2 rounded text-white ${listening ? "bg-red-500" : "bg-neon-green"}`}
//         >
//           {listening ? "Listening..." : "Click to Talk"}
//         </button>
//       </div>
//     </div>
//   );
// }



//Working with latency
// import React, { useState, useEffect } from "react";

// export default function App() {
//   const [messages, setMessages] = useState([]);
//   const [listening, setListening] = useState(false);
//   const [userInput, setUserInput] = useState("");

//   useEffect(() => {
//     if (!("webkitSpeechRecognition" in window)) {
//       console.warn("Speech recognition not supported in this browser.");
//       return;
//     }

//     let recognition = new webkitSpeechRecognition();
//     recognition.continuous = false;
//     recognition.lang = "en-US";

//     recognition.onstart = () => setListening(true);
//     recognition.onend = () => setListening(false);
//     recognition.onresult = (event) => {
//       const transcript = event.results[0][0].transcript;
//       handleUserInput(transcript);
//     };

//     if (listening) {
//       recognition.start();
//     }

//     return () => {
//       recognition.onend = null;
//       recognition.stop();
//     };
//   }, [listening]);

//   const handleUserInput = async (text) => {
//     if (!text || text.trim() === "") return;

//     setMessages((prev) => [...prev, { sender: "You", text }]);
//     setUserInput("");

//     const startTime = performance.now();
//     try {
//       const response = await fetch("http://127.0.0.1:5000/chat", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ message: text }),
//       });

//       const endTime = performance.now();
//       const latency = (endTime - startTime).toFixed(2) + " ms";

//       if (!response.ok) throw new Error("Failed to fetch response");

//       const data = await response.json();
//       setMessages((prev) => [
//         ...prev,
//         { sender: "Bot", text: data.response, latency }
//       ]);
//     } catch (error) {
//       console.error("Error fetching response:", error);
//     }
//   };

//   return (
//     <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white p-4">
//       <h1 className="text-3xl font-bold mb-4 text-neon-blue">Loan Voice Assistant</h1>
//       <div className="w-full max-w-md bg-gray-800 shadow-lg rounded-lg p-4 h-96 overflow-y-auto border border-neon-blue">
//         {messages.map((msg, index) => (
//           <p key={index} className={`p-2 ${msg.sender === "You" ? "text-pink" : "text-green"}`}>
//             <strong>{msg.sender}:</strong> {msg.text} {msg.latency && <span className="text-gray-400">({msg.latency})</span>}
//           </p>
//         ))}
//       </div>
//       <div className="flex w-full max-w-md mt-4">
//         <input
//           type="text"
//           className="flex-1 p-2 border border-neon-blue bg-gray-700 text-white rounded-l focus:outline-none"
//           value={userInput}
//           onChange={(e) => setUserInput(e.target.value)}
//           placeholder="Type a message..."
//         />
//         <button
//           onClick={() => handleUserInput(userInput)}
//           className="bg-neon-blue text-white p-2 cursor-pointer"
//         >
//           Send
//         </button>
//         <button
//           onClick={() => setListening(true)}
//           className={`p-2 ml-2 rounded text-white cursor-pointer ${listening ? "bg-red-500" : "bg-neon-green"}`}
//         >
//           {listening ? "Listening..." : "Click to Talk"}
//         </button>
//       </div>
//     </div>
//   );
// }





import React, { useState, useEffect } from "react";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [listening, setListening] = useState(false);
  const [userInput, setUserInput] = useState("");

  useEffect(() => {
    if (!("webkitSpeechRecognition" in window)) {
      console.warn("Speech recognition not supported in this browser.");
      return;
    }

    let recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.lang = "en-US";

    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      handleUserInput(transcript);
    };

    if (listening) {
      recognition.start();
    }

    return () => {
      recognition.onend = null;
      recognition.stop();
    };
  }, [listening]);

  const handleUserInput = async (text) => {
    if (!text || text.trim() === "") return;

    setMessages((prev) => [...prev, { sender: "You", text }]);
    setUserInput("");

    const startTime = performance.now();
    try {
      const response = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      const endTime = performance.now();
      const latency = (endTime - startTime).toFixed(2) + " ms";

      if (!response.ok) throw new Error("Failed to fetch response");

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { sender: "Bot", text: data.response, latency }
      ]);
    } catch (error) {
      console.error("Error fetching response:", error);
    }
  };

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = "http://127.0.0.1:5000/download-log";
    link.setAttribute("download", "chat_log.txt");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white p-4">
      <h1 className="text-3xl font-bold mb-4 text-neon-blue">Loan Voice Assistant</h1>
      <div className="w-full max-w-md bg-gray-800 shadow-lg rounded-lg p-4 h-96 overflow-y-auto border border-neon-blue">
        {messages.map((msg, index) => (
          <p key={index} className={`p-2 ${msg.sender === "You" ? "text-pink" : "text-green"}`}>
            <strong>{msg.sender}:</strong> {msg.text} {msg.latency && <span className="text-gray-400">({msg.latency})</span>}
          </p>
        ))}
      </div>
      <div className="flex w-full max-w-md mt-4">
        <input
          type="text"
          className="flex-1 p-2 border border-neon-blue bg-gray-700 text-white rounded-l focus:outline-none"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          placeholder="Type a message..."
        />
        <button
          onClick={() => handleUserInput(userInput)}
          className="bg-neon-blue text-white p-2 cursor-pointer"
        >
          Send
        </button>
        <button
          onClick={() => setListening(true)}
          className={`p-2 ml-2 rounded text-white cursor-pointer ${listening ? "bg-red-500" : "bg-neon-green"}`}
        >
          {listening ? "Listening..." : "Click to Talk"}
        </button>
      </div>
      <button
        onClick={handleDownload}
        className="mt-4 bg-neon-blue text-white p-2 rounded cursor-pointer"
      >
        Download Chat Log
      </button>
    </div>
  );
}

