import React from 'react';
import { Sidebar, NavigationPage } from './Sidebar';
import { Header } from './Header';

interface AppLayoutProps {
  currentPage: NavigationPage;
  onNavigate: (page: NavigationPage) => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentPage,
  onNavigate,
  onRefresh,
  isRefreshing,
  children,
}) => {
  return (
    <div className="flex h-screen w-screen bg-sentinel-bg overflow-hidden text-sentinel-text">
      {/* Left Sidebar */}
      <Sidebar currentPage={currentPage} onNavigate={onNavigate} />

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <Header
          currentPage={currentPage}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
        />

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-6 bg-sentinel-bg">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
};
