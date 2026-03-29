import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/layout";
import { DashboardPage } from "@/pages/dashboard";
import { TransactionsPage } from "@/pages/transactions";
import { ReconciliationsPage } from "@/pages/reconciliations";
import { ReconciliationDetailPage } from "@/pages/reconciliation-detail";
import { AskPage } from "@/pages/ask";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/reconciliations" element={<ReconciliationsPage />} />
          <Route path="/reconciliations/:id" element={<ReconciliationDetailPage />} />
          <Route path="/ask" element={<AskPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
