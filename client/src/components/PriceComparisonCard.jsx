import { useEffect, useState } from "react";

import {
  createGoalPrice,
  deleteGoalPrice,
  getGoalPrices,
  refreshGoalPrices,
  refreshRetailerPrice,
  updateGoalPrice,
} from "../services/api";

function formatCurrency(amount) {
  return Number(amount || 0).toFixed(2);
}

function formatDateTime(value) {
  if (!value) return "Never";

  return new Date(value).toLocaleString();
}

function PriceComparisonCard({ goalId }) {
  const [prices, setPrices] = useState([]);
  const [summary, setSummary] = useState(null);
  const [formData, setFormData] = useState({
    retailer_name: "",
    product_url: "",
    price: "",
    shipping_cost: "",
    tax_estimate: "",
    is_preferred: false,
    note: "",
  });

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRefreshingAll, setIsRefreshingAll] = useState(false);
  const [refreshingPriceId, setRefreshingPriceId] = useState(null);

  async function loadPrices() {
    if (!goalId) return;

    setIsLoading(true);
    setError("");

    try {
      const data = await getGoalPrices(goalId);
      setPrices(data.prices || []);
      setSummary(data.summary || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadPrices();
  }, [goalId]);

  function handleChange(event) {
    const { name, value, type, checked } = event.target;

    setFormData((currentData) => ({
      ...currentData,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setMessage("");

    if (!formData.retailer_name.trim()) {
      setError("Retailer name is required.");
      return;
    }

    const price = Number(formData.price);

    if (Number.isNaN(price) || price < 0) {
      setError("Price must be a valid positive number.");
      return;
    }

    setIsSaving(true);

    try {
      const data = await createGoalPrice(goalId, {
        retailer_name: formData.retailer_name.trim(),
        product_url: formData.product_url.trim(),
        price,
        shipping_cost:
          formData.shipping_cost === "" ? 0 : Number(formData.shipping_cost),
        tax_estimate:
          formData.tax_estimate === "" ? 0 : Number(formData.tax_estimate),
        is_preferred: formData.is_preferred,
        note: formData.note.trim(),
      });

      setPrices((currentPrices) => {
        const updatedPrices = data.price.is_preferred
          ? currentPrices.map((priceItem) => ({
              ...priceItem,
              is_preferred: false,
            }))
          : currentPrices;

        return [data.price, ...updatedPrices];
      });

      setSummary(data.summary);
      setMessage("Retailer price added successfully.");

      setFormData({
        retailer_name: "",
        product_url: "",
        price: "",
        shipping_cost: "",
        tax_estimate: "",
        is_preferred: false,
        note: "",
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSetPreferred(priceItem) {
    setError("");
    setMessage("");

    try {
      const data = await updateGoalPrice(priceItem.id, {
        is_preferred: true,
      });

      setPrices((currentPrices) =>
        currentPrices.map((currentPrice) =>
          currentPrice.id === priceItem.id
            ? data.price
            : { ...currentPrice, is_preferred: false }
        )
      );

      setSummary(data.summary);
      setMessage(`${priceItem.retailer_name} set as preferred retailer.`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleToggleActive(priceItem) {
    setError("");
    setMessage("");

    try {
      const data = await updateGoalPrice(priceItem.id, {
        is_active: !priceItem.is_active,
      });

      setPrices((currentPrices) =>
        currentPrices.map((currentPrice) =>
          currentPrice.id === priceItem.id ? data.price : currentPrice
        )
      );

      setSummary(data.summary);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(priceId) {
    setError("");
    setMessage("");

    try {
      const data = await deleteGoalPrice(priceId);

      setPrices((currentPrices) =>
        currentPrices.filter((priceItem) => priceItem.id !== priceId)
      );

      setSummary(data.summary);
      setMessage("Retailer price deleted.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRefreshOne(priceItem) {
    setError("");
    setMessage("");
    setRefreshingPriceId(priceItem.id);

    try {
      const data = await refreshRetailerPrice(priceItem.id);

      setPrices((currentPrices) =>
        currentPrices.map((currentPrice) =>
          currentPrice.id === priceItem.id ? data.price : currentPrice
        )
      );

      setSummary(data.summary);

      const difference = data.result?.difference || 0;

      if (difference < 0) {
        setMessage(
          `${priceItem.retailer_name} dropped by $${formatCurrency(
            Math.abs(difference)
          )}.`
        );
      } else if (difference > 0) {
        setMessage(
          `${priceItem.retailer_name} increased by $${formatCurrency(
            difference
          )}.`
        );
      } else {
        setMessage(`${priceItem.retailer_name} price checked. No change.`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshingPriceId(null);
    }
  }

  async function handleRefreshAll() {
    setError("");
    setMessage("");
    setIsRefreshingAll(true);

    try {
      const data = await refreshGoalPrices(goalId);

      setPrices(data.prices || []);
      setSummary(data.summary || null);

      setMessage(
        `Live price check complete. ${data.updated_count} updated, ${data.failed_count} failed.`
      );

      if (data.failed_count > 0) {
        const failedResult = data.results.find(
          (result) => result.status === "failed"
        );

        if (failedResult?.error) {
          setError(`Some prices could not refresh: ${failedResult.error}`);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRefreshingAll(false);
    }
  }

  const hasRefreshablePrices = prices.some(
    (priceItem) => priceItem.is_active && priceItem.product_url
  );

  return (
    <section className="goal-detail-card price-comparison-card">
      <div className="section-header">
        <div>
          <p className="eyebrow">Price tracking</p>
          <h2>Store Price Comparison</h2>
        </div>

        <div className="price-header-actions">
          <p>
            Track retailer prices manually or refresh live prices from saved
            product URLs.
          </p>

          <button
            type="button"
            className="secondary-action"
            disabled={!hasRefreshablePrices || isRefreshingAll}
            onClick={handleRefreshAll}
          >
            {isRefreshingAll ? "Checking live prices..." : "Check Live Prices"}
          </button>
        </div>
      </div>

      {error && <p className="error-message">{error}</p>}
      {message && <p className="success-message">{message}</p>}

      {summary && (
        <div className="price-summary-grid">
          <div>
            <span>Tracked Stores</span>
            <strong>{summary.price_count}</strong>
          </div>

          <div>
            <span>Lowest Price</span>
            <strong>
              {summary.lowest_price
                ? `$${formatCurrency(summary.lowest_price.total_price)}`
                : "$0.00"}
            </strong>
          </div>

          <div>
            <span>Best Store</span>
            <strong>
              {summary.lowest_price
                ? summary.lowest_price.retailer_name
                : "None yet"}
            </strong>
          </div>

          <div>
            <span>Average Price</span>
            <strong>${formatCurrency(summary.average_total_price)}</strong>
          </div>
        </div>
      )}

      <form className="price-form" onSubmit={handleSubmit}>
        <div className="price-field">
          <label htmlFor="retailer_name">Retailer</label>
          <input
            id="retailer_name"
            name="retailer_name"
            type="text"
            placeholder="Best Buy"
            value={formData.retailer_name}
            onChange={handleChange}
            required
          />
        </div>

        <div className="price-field">
          <label htmlFor="price">Price</label>
          <input
            id="price"
            name="price"
            type="number"
            min="0"
            step="0.01"
            placeholder="499.99"
            value={formData.price}
            onChange={handleChange}
            required
          />
        </div>

        <div className="price-field">
          <label htmlFor="shipping_cost">Shipping</label>
          <input
            id="shipping_cost"
            name="shipping_cost"
            type="number"
            min="0"
            step="0.01"
            placeholder="0"
            value={formData.shipping_cost}
            onChange={handleChange}
          />
        </div>

        <div className="price-field">
          <label htmlFor="tax_estimate">Tax Estimate</label>
          <input
            id="tax_estimate"
            name="tax_estimate"
            type="number"
            min="0"
            step="0.01"
            placeholder="0"
            value={formData.tax_estimate}
            onChange={handleChange}
          />
        </div>

        <div className="price-field price-field-wide">
          <label htmlFor="product_url">Product URL</label>
          <input
            id="product_url"
            name="product_url"
            type="url"
            placeholder="https://..."
            value={formData.product_url}
            onChange={handleChange}
          />
        </div>

        <div className="price-field price-field-wide">
          <label htmlFor="note">Note</label>
          <input
            id="note"
            name="note"
            type="text"
            placeholder="Optional note"
            value={formData.note}
            onChange={handleChange}
          />
        </div>

        <label className="price-checkbox">
          <input
            name="is_preferred"
            type="checkbox"
            checked={formData.is_preferred}
            onChange={handleChange}
          />
          Preferred retailer
        </label>

        <button type="submit" disabled={isSaving}>
          {isSaving ? "Adding price..." : "Add Retailer Price"}
        </button>
      </form>

      {isLoading ? (
        <p className="advisor-muted">Loading prices...</p>
      ) : prices.length > 0 ? (
        <div className="price-list">
          {prices.map((priceItem) => (
            <article
              className={`price-item ${priceItem.is_active ? "" : "inactive"}`}
              key={priceItem.id}
            >
              <div>
                <div className="price-item-heading">
                  <h3>{priceItem.retailer_name}</h3>

                  {priceItem.is_preferred && (
                    <span className="price-pill">Preferred</span>
                  )}

                  {summary?.lowest_price?.id === priceItem.id && (
                    <span className="price-pill best">Lowest</span>
                  )}
                </div>

                <p>
                  ${formatCurrency(priceItem.total_price)} total · $
                  {formatCurrency(priceItem.price)} base
                </p>

                {(priceItem.shipping_cost > 0 ||
                  priceItem.tax_estimate > 0) && (
                  <span>
                    Shipping ${formatCurrency(priceItem.shipping_cost)} · Tax $
                    {formatCurrency(priceItem.tax_estimate)}
                  </span>
                )}

                <span>Last checked: {formatDateTime(priceItem.last_checked_at)}</span>

                {priceItem.note && <span>{priceItem.note}</span>}

                {priceItem.product_url && (
                  <a
                    href={priceItem.product_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    View product
                  </a>
                )}
              </div>

              <div className="price-item-actions">
                {priceItem.product_url && priceItem.is_active && (
                  <button
                    type="button"
                    disabled={refreshingPriceId === priceItem.id}
                    onClick={() => handleRefreshOne(priceItem)}
                  >
                    {refreshingPriceId === priceItem.id
                      ? "Refreshing..."
                      : "Refresh Price"}
                  </button>
                )}

                {!priceItem.is_preferred && (
                  <button
                    type="button"
                    onClick={() => handleSetPreferred(priceItem)}
                  >
                    Set Preferred
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => handleToggleActive(priceItem)}
                >
                  {priceItem.is_active ? "Pause" : "Activate"}
                </button>

                <button type="button" onClick={() => handleDelete(priceItem.id)}>
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state compact">
          <p>No retailer prices added yet.</p>
        </div>
      )}
    </section>
  );
}

export default PriceComparisonCard;