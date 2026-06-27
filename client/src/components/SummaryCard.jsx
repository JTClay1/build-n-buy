function SummaryCard({ label, value }) {
  return (
    <div className="summary-card">
      <p>{label}</p>
      <h2>{value}</h2>
    </div>
  );
}

export default SummaryCard;