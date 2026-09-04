import { useState } from 'react';
import { AppLayout } from './layouts/AppLayout';
import { NavigationPage } from './layouts/Sidebar';
import { RiskOverviewPage } from './pages/RiskOverviewPage';
import { InvestigatePage } from './pages/InvestigatePage';
import { EvaluationPage } from './pages/EvaluationPage';

export function App() {
  const getInitialPage = (): NavigationPage => {
    const hash = window.location.hash.replace('#', '');
    if (hash === 'evaluation' || hash === 'investigate' || hash === 'risk-overview') {
      return hash as NavigationPage;
    }
    return 'risk-overview';
  };

  const [currentPage, setCurrentPage] = useState<NavigationPage>(getInitialPage);
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const handleNavigate = (page: NavigationPage) => {
    window.location.hash = page;
    setCurrentPage(page);
  };

  const handleRefresh = () => {
    setIsRefreshing(true);
    setRefreshTrigger((prev) => prev + 1);
    setTimeout(() => setIsRefreshing(false), 600);
  };

  const handleNavigateToInvestigate = (entityValue?: string) => {
    if (entityValue) {
      setSelectedEntity(entityValue);
    }
    handleNavigate('investigate');
  };

  return (
    <AppLayout
      currentPage={currentPage}
      onNavigate={handleNavigate}
      onRefresh={handleRefresh}
      isRefreshing={isRefreshing}
    >
      <div key={refreshTrigger}>
        {currentPage === 'risk-overview' && (
          <RiskOverviewPage
            onNavigateToInvestigate={handleNavigateToInvestigate}
          />
        )}
        {currentPage === 'investigate' && (
          <InvestigatePage targetEntity={selectedEntity} />
        )}
        {currentPage === 'evaluation' && <EvaluationPage />}
      </div>
    </AppLayout>
  );
}

export default App;
