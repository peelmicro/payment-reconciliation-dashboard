import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Layout } from "@/components/layout";

describe("Layout", () => {
  function renderLayout() {
    return render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );
  }

  it("renders the app title", () => {
    renderLayout();
    expect(screen.getByText("Payment Reconciliation")).toBeInTheDocument();
  });

  it("renders all navigation links", () => {
    renderLayout();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Transactions")).toBeInTheDocument();
    expect(screen.getByText("Reconciliations")).toBeInTheDocument();
    expect(screen.getByText("Ask AI")).toBeInTheDocument();
  });

  it("navigation links have the correct hrefs", () => {
    renderLayout();
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Transactions" })).toHaveAttribute("href", "/transactions");
    expect(screen.getByRole("link", { name: "Reconciliations" })).toHaveAttribute("href", "/reconciliations");
    expect(screen.getByRole("link", { name: "Ask AI" })).toHaveAttribute("href", "/ask");
  });
});
