import { type ReactNode } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import AuthPage from './pages/AuthPage'
import LandingPage from './pages/LandingPage'
import CreationPage from './pages/CreationPage'
import ProfilePage from './pages/ProfilePage'
import StoryDraft from './pages/editor/StoryDraft'
import LiteratureReview from './pages/editor/LiteratureReview'
import ScienceReview from './pages/editor/ScienceReview'
import ReaderFeedback from './pages/editor/ReaderFeedback'
import DrawingSettings from './pages/editor/DrawingSettings'
import Illustration from './pages/editor/Illustration'
import IllustrationReview from './pages/editor/IllustrationReview'
import PublishLayout from './pages/editor/PublishLayout'
import KnowledgeGraph from './pages/editor/KnowledgeGraph'
import KnowledgeGraphEntities from './pages/editor/KnowledgeGraphEntities'
import { isLoggedIn } from './lib/auth'

function ProtectedRoute({ children }: { children: ReactNode }) {
  if (!isLoggedIn()) {
    return <Navigate to="/" replace />;
  }
  return children;
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<AuthPage />} />
        <Route path="/home" element={<ProtectedRoute><LandingPage /></ProtectedRoute>} />
        
        {/* 单独的创作表单页 */}
        <Route path="/creation" element={<ProtectedRoute><CreationPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/knowledge-graph" element={<ProtectedRoute><KnowledgeGraph /></ProtectedRoute>} />
        <Route path="/knowledge-graph/entities" element={<ProtectedRoute><KnowledgeGraphEntities /></ProtectedRoute>} />

        {/* 项目编辑器页（带顶部信息和Tab） */}
        <Route path="/editor" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Navigate to="draft" replace />} />
          <Route path="draft" element={<StoryDraft />} />
          <Route path="literature-review" element={<LiteratureReview />} />
          <Route path="science-review" element={<ScienceReview />} />
          <Route path="reader-feedback" element={<ReaderFeedback />} />
          <Route path="drawing-settings" element={<DrawingSettings />} />
          <Route path="illustration" element={<Illustration />} />
          <Route path="illustration-review" element={<IllustrationReview />} />
          <Route path="layout" element={<PublishLayout />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </Router>
  )
}