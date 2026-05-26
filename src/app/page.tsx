
export default function Home() {
  const callLogData = [
    { date: "2026-05-24", direction: "Outgoing", num_calls: 1, duration_raw: "", duration_sec: "", notes: "" },
    { date: "2026-05-19", direction: "Incoming", num_calls: 1, duration_raw: "2m", duration_sec: 120, notes: "" },
    { date: "2026-05-18", direction: "Incoming", num_calls: 1, duration_raw: "3m", duration_sec: 180, notes: "" },
    { date: "2026-05-14", direction: "Incoming", num_calls: 1, duration_raw: "1m", duration_sec: 60, notes: "" },
    { date: "2026-05-12", direction: "Incoming", num_calls: 1, duration_raw: "12m", duration_sec: 720, notes: "" },
    { date: "2026-05-10", direction: "Incoming", num_calls: 2, duration_raw: "6m", duration_sec: 360, notes: "" },
    { date: "2026-05-07", direction: "Outgoing", num_calls: 3, duration_raw: "", duration_sec: "", notes: "" },
    { date: "2026-05-04", direction: "Outgoing", num_calls: 1, duration_raw: "3m", duration_sec: 180, notes: "" },
    { date: "2026-04-28", direction: "Incoming", num_calls: 1, duration_raw: "2m5s", duration_sec: 125, notes: "" },
    { date: "2026-04-26", direction: "Outgoing", num_calls: 4, duration_raw: "7m3s", duration_sec: 423, notes: "" },
    { date: "2026-04-23", direction: "Incoming", num_calls: 1, duration_raw: "42s", duration_sec: 42, notes: "" },
    { date: "2026-04-16", direction: "Incoming", num_calls: 5, duration_raw: "7m", duration_sec: 420, notes: "" },
    { date: "2026-04-14", direction: "Incoming", num_calls: 6, duration_raw: "4m", duration_sec: 240, notes: "" },
    { date: "2026-04-13", direction: "Outgoing", num_calls: 2, duration_raw: "", duration_sec: "", notes: "" },
    { date: "2026-04-12", direction: "Incoming", num_calls: 3, duration_raw: "4m", duration_sec: 240, notes: "" },
    { date: "2026-04-11", direction: "Outgoing", num_calls: 1, duration_raw: "", duration_sec: "", notes: "" },
    { date: "2026-04-09", direction: "Incoming", num_calls: 1, duration_raw: "3m4s", duration_sec: 184, notes: "" },
    { date: "2026-04-07", direction: "Incoming", num_calls: 2, duration_raw: "", duration_sec: "", notes: "" },
    { date: "2026-04-05", direction: "Incoming", num_calls: 1, duration_raw: "2s", duration_sec: 2, notes: "" },
    { date: "2026-03-23", direction: "Outgoing", num_calls: 2, duration_raw: "14m", duration_sec: 840, notes: "" },
    { date: "2026-03-17", direction: "Incoming", num_calls: 2, duration_raw: "2m", duration_sec: 120, notes: "" },
    { date: "2026-03-15", direction: "Incoming", num_calls: 1, duration_raw: "", duration_sec: "", notes: "" },
    { date: "2026-03-12", direction: "Incoming", num_calls: 6, duration_raw: "6m", duration_sec: 360, notes: "" },
    { date: "2026-03-11", direction: "Incoming", num_calls: 2, duration_raw: "", duration_sec: "", notes: "" },
    { date: "2026-03-10", direction: "Incoming", num_calls: 2, duration_raw: "", duration_sec: "", notes: "" },
    { date: "2026-03-05", direction: "Incoming", num_calls: 3, duration_raw: "", duration_sec: "", notes: "" },
    { date: "2026-03-04", direction: "Incoming", num_calls: 1, duration_raw: "4m", duration_sec: 240, notes: "" },
    { date: "2026-03-01", direction: "Incoming", num_calls: 2, duration_raw: "12m", duration_sec: 720, notes: "" },
    { date: "2026-02-24", direction: "Incoming", num_calls: 2, duration_raw: "1m", duration_sec: 60, notes: "" },
    { date: "2026-02-19", direction: "Incoming", num_calls: 1, duration_raw: "2m", duration_sec: 120, notes: "" },
    { date: "2026-02-17", direction: "Incoming", num_calls: 2, duration_raw: "8m7s", duration_sec: 487, notes: "" },
    { date: "2026-02-16", direction: "Outgoing", num_calls: 5, duration_raw: "11m", duration_sec: 660, notes: "" },
    { date: "2026-02-15", direction: "Outgoing", num_calls: 3, duration_raw: "5m", duration_sec: 300, notes: "" },
    { date: "2026-02-14", direction: "Incoming", num_calls: 3, duration_raw: "8m", duration_sec: 480, notes: "" },
    { date: "2026-02-12", direction: "Incoming", num_calls: 1, duration_raw: "3m", duration_sec: 180, notes: "" },
    { date: "2026-02-10", direction: "Incoming", num_calls: 2, duration_raw: "1m", duration_sec: 60, notes: "" },
    { date: "2026-02-09", direction: "Incoming", num_calls: 5, duration_raw: "9m", duration_sec: 540, notes: "" },
    { date: "2026-02-08", direction: "Outgoing", num_calls: 1, duration_raw: "3m", duration_sec: 180, notes: "" },
    { date: "2026-02-05", direction: "Incoming", num_calls: 2, duration_raw: "7m1s", duration_sec: 421, notes: "" },
    { date: "2026-02-03", direction: "Outgoing", num_calls: 1, duration_raw: "1m", duration_sec: 60, notes: "" },
    { date: "2026-02-01", direction: "Incoming", num_calls: 1, duration_raw: "2m", duration_sec: 120, notes: "" },
    { date: "2026-01-29", direction: "Incoming", num_calls: 1, duration_raw: "5m", duration_sec: 300, notes: "" },
    { date: "2026-01-27", direction: "Incoming", num_calls: 3, duration_raw: "7m", duration_sec: 420, notes: "" },
    { date: "2026-01-18", direction: "Incoming", num_calls: 2, duration_raw: "1m", duration_sec: 60, notes: "" },
    { date: "2026-01-17", direction: "Incoming", num_calls: 2, duration_raw: "3m", duration_sec: 180, notes: "" },
    { date: "2026-01-15", direction: "Incoming", num_calls: 1, duration_raw: "1m", duration_sec: 60, notes: "" },
    { date: "2026-01-13", direction: "Incoming", num_calls: 1, duration_raw: "7m", duration_sec: 420, notes: "" },
    { date: "2026-01-08", direction: "Outgoing", num_calls: 1, duration_raw: "4m", duration_sec: 240, notes: "" },
  ];

  return (
    <main className="min-h-screen bg-neutral-900 text-neutral-100 p-8">
      <h1 className="text-4xl font-bold mb-8 text-center">Call Log</h1>
      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead>
            <tr className="bg-neutral-800">
              <th className="px-4 py-2 text-left">Date</th>
              <th className="px-4 py-2 text-left">Direction</th>
              <th className="px-4 py-2 text-left">Num Calls</th>
              <th className="px-4 py-2 text-left">Duration Raw</th>
              <th className="px-4 py-2 text-left">Duration Sec</th>
              <th className="px-4 py-2 text-left">Notes</th>
            </tr>
          </thead>
          <tbody>
            {callLogData.map((log, index) => (
              <tr key={index} className={index % 2 === 0 ? "bg-neutral-700" : "bg-neutral-800"}>
                <td className="border px-4 py-2">{log.date}</td>
                <td className="border px-4 py-2">{log.direction}</td>
                <td className="border px-4 py-2">{log.num_calls}</td>
                <td className="border px-4 py-2">{log.duration_raw}</td>
                <td className="border px-4 py-2">{log.duration_sec}</td>
                <td className="border px-4 py-2">{log.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}

