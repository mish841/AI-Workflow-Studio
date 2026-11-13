import { useState } from "react";
import { AppShell } from "./components/AppShell";
import { AssessmentsPage } from "./components/AssessmentsPage";
import { ComparePage } from "./components/ComparePage";
import { DocumentsPage } from "./components/DocumentsPage";
import { FindingsPage } from "./components/FindingsPage";
import { WorkspaceReviewPage } from "./components/WorkspaceReviewPage";
import { WorkspacesPage } from "./components/WorkspacesPage";
import {
  ApiError,
  LIVE_EVALUATION_TIMEOUT_MS,
  createLiveEvaluation,
  createWorkspaceReview,
  fetchWorkspaceDocuments,
} from "./lib/api";
import {
  mapLiveResult,
  mapReviewResult,
  mapSampleResult,
  WORKSPACE_TITLES,
} from "./lib/assessment";
import { dataset } from "./lib/dataset";
import { DOCUMENT_GROUPS, WORKSPACE_REVIEW_COPY } from "./lib/workspaces";
import type {
  AssessmentRun,
  DatasetDocument,
  PolicyVersion,
  View,
  WorkspaceId,
} from "./types";
import "./App.css";

export default function App() {
  const [view, setView] = useState<View>("workspaces");
  const [workspace, setWorkspace] = useState<WorkspaceId>("security");
  const [selectedPolicy, setSelectedPolicy] = useState<PolicyVersion>("v1");
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<Partial<Record<WorkspaceId, AssessmentRun>>>({});
  const [runsByPolicy, setRunsByPolicy] = useState<
    Partial<Record<PolicyVersion, AssessmentRun>>
  >({});
  const [workspaceDocs, setWorkspaceDocs] = useState<
    Partial<Record<Exclude<WorkspaceId, "security">, DatasetDocument[]>>
  >({});
  const [docError, setDocError] = useState<string | null>(null);

  const run = runs[workspace] ?? null;

  function navigate(next: View) {
    if (next === "compare" && workspace !== "security") {
      setView("documents");
      return;
    }
    setView(next);
  }

  async function loadWorkspaceDocs(id: Exclude<WorkspaceId, "security">) {
    setDocError(null);
    try {
      const documents = await fetchWorkspaceDocuments(id);
      setWorkspaceDocs((current) => ({ ...current, [id]: documents }));
    } catch (caught) {
      setDocError(
        caught instanceof ApiError
          ? caught.message
          : "Could not load workspace documents.",
      );
    }
  }

  function openWorkspace(next: WorkspaceId) {
    setWorkspace(next);
    setView("documents");
    setError(null);
    if (next !== "security") {
      void loadWorkspaceDocs(next);
    }
  }

  async function runLive() {
    setError(null);
    setIsRunning(true);
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), LIVE_EVALUATION_TIMEOUT_MS);
    try {
      const result = await createLiveEvaluation(
        selectedPolicy,
        controller.signal,
      );
      const mapped = mapLiveResult(result);
      setRuns((current) => ({ ...current, security: mapped }));
      setRunsByPolicy((current) => ({
        ...current,
        [mapped.policyVersion as PolicyVersion]: mapped,
      }));
    } catch (caught) {
      const message =
        caught instanceof ApiError
          ? caught.message
          : "Assessment failed. Please try again.";
      setError(message);
    } finally {
      window.clearTimeout(timer);
      setIsRunning(false);
    }
  }

  function loadSample() {
    setError(null);
    const mapped = mapSampleResult(dataset.requirements, selectedPolicy);
    setRuns((current) => ({ ...current, security: mapped }));
    setRunsByPolicy((current) => ({
      ...current,
      [selectedPolicy]: mapped,
    }));
  }

  async function runReview(id: Exclude<WorkspaceId, "security">) {
    setError(null);
    setIsRunning(true);
    try {
      const result = await createWorkspaceReview(id);
      setRuns((current) => ({ ...current, [id]: mapReviewResult(result) }));
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Review failed. Please try again.",
      );
    } finally {
      setIsRunning(false);
    }
  }

  const inWorkspace = view !== "workspaces";
  const reviewWorkspace =
    inWorkspace && workspace !== "security" ? workspace : null;
  const securityViews = inWorkspace && workspace === "security";
  const currentDocs =
    workspace === "security"
      ? dataset.documents
      : workspaceDocs[workspace] ?? [];

  return (
    <AppShell view={view} workspace={workspace} onNavigate={navigate}>
      {view === "workspaces" && <WorkspacesPage onOpen={openWorkspace} />}
      {inWorkspace && view === "documents" && (
        <>
          {docError && workspace !== "security" ? (
            <p className="error-banner" role="alert">
              {docError}
            </p>
          ) : null}
          <DocumentsPage
            key={workspace}
            documents={currentDocs}
            groups={DOCUMENT_GROUPS[workspace]}
          />
        </>
      )}
      {securityViews && view === "assessments" && (
        <AssessmentsPage
          policies={dataset.documents.filter((doc) => doc.kind === "policy")}
          selectedPolicy={selectedPolicy}
          onSelectPolicy={setSelectedPolicy}
          isRunning={isRunning}
          error={error}
          run={run}
          onRunLive={runLive}
          onLoadSample={loadSample}
          onViewFindings={() => setView("findings")}
        />
      )}
      {reviewWorkspace && view === "assessments" && (
        <WorkspaceReviewPage
          title={WORKSPACE_TITLES[reviewWorkspace]}
          summary={WORKSPACE_REVIEW_COPY[reviewWorkspace].summary}
          disclaimer={WORKSPACE_REVIEW_COPY[reviewWorkspace].disclaimer}
          isRunning={isRunning}
          error={error}
          run={run}
          onRun={() => void runReview(reviewWorkspace)}
          onViewFindings={() => setView("findings")}
        />
      )}
      {inWorkspace && view === "findings" && (
        <FindingsPage
          key={run ? `${workspace}-${run.evaluationId ?? "empty"}` : `${workspace}-empty`}
          run={run}
          onGoAssess={() => setView("assessments")}
        />
      )}
      {securityViews && view === "compare" && (
        <ComparePage
          policies={dataset.documents.filter((doc) => doc.kind === "policy")}
          requirements={dataset.requirements}
          liveRuns={runsByPolicy}
        />
      )}
    </AppShell>
  );
}
