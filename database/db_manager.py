"""SQLite database manager and repository operations."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Iterator, List, Optional

import pandas as pd

from models.schemas import (
    CompletenessSummary,
    FunctionalRequirement,
    MissingInformationItem,
    NonFunctionalRequirement,
    ProjectAnalysisRecord,
    ProjectMilestone,
    TechStackRecommendation,
)


class DatabaseError(RuntimeError):
    """Raised when a database operation fails."""


class DatabaseManager:
    """Handles SQLite connection lifecycle, schema initialization, and CRUD queries."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a SQLite connection with foreign keys enabled and row factory set."""
        conn = sqlite3.connect(str(self.db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise DatabaseError(f"Database operation failed: {exc}") from exc
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Create normalized tables if they do not already exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_title TEXT NOT NULL,
            client_name TEXT NOT NULL,
            engagement_type TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_filename TEXT,
            raw_input_text TEXT NOT NULL,
            executive_summary TEXT NOT NULL,
            project_domain TEXT NOT NULL,
            target_users_json TEXT NOT NULL,
            assumptions_json TEXT NOT NULL,
            completeness_score REAL NOT NULL,
            readiness_status TEXT NOT NULL,
            score_breakdown_json TEXT NOT NULL,
            model_used TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS functional_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            req_code TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            category TEXT NOT NULL,
            acceptance_criteria TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS non_functional_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            req_code TEXT NOT NULL,
            category TEXT NOT NULL,
            requirement TEXT NOT NULL,
            priority TEXT NOT NULL,
            metric_target TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tech_stack_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            layer TEXT NOT NULL,
            technology TEXT NOT NULL,
            rationale TEXT NOT NULL,
            alternatives_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            phase_number INTEGER NOT NULL,
            phase_name TEXT NOT NULL,
            duration_weeks INTEGER NOT NULL,
            start_week INTEGER NOT NULL,
            end_week INTEGER NOT NULL,
            deliverables_json TEXT NOT NULL,
            dependencies TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS missing_information (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            area TEXT NOT NULL,
            severity TEXT NOT NULL,
            missing_detail TEXT NOT NULL,
            clarifying_question TEXT NOT NULL,
            impact TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_fr_analysis_id ON functional_requirements(analysis_id);
        CREATE INDEX IF NOT EXISTS idx_nfr_analysis_id ON non_functional_requirements(analysis_id);
        """
        with self._connect() as conn:
            conn.executescript(schema_sql)

    def save_analysis(self, record: ProjectAnalysisRecord) -> int:
        """Persist a full analysis and all child entities inside one transaction."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO analyses (
                    project_title, client_name, engagement_type, source_type,
                    source_filename, raw_input_text, executive_summary, project_domain,
                    target_users_json, assumptions_json, completeness_score,
                    readiness_status, score_breakdown_json, model_used,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.project_title,
                    record.client_name,
                    record.engagement_type,
                    record.source_type,
                    record.source_filename,
                    record.raw_input_text,
                    record.executive_summary,
                    record.project_domain,
                    json.dumps(record.target_users),
                    json.dumps(record.assumptions),
                    float(record.completeness_score),
                    record.readiness_status,
                    record.score_breakdown.model_dump_json(),
                    record.model_used,
                    now_iso,
                    now_iso,
                ),
            )
            analysis_id = int(cursor.lastrowid)

            conn.executemany(
                """
                INSERT INTO functional_requirements (
                    analysis_id, req_code, title, description, priority, category, acceptance_criteria
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        analysis_id,
                        item.req_code,
                        item.title,
                        item.description,
                        item.priority,
                        item.category,
                        item.acceptance_criteria,
                    )
                    for item in record.functional_requirements
                ],
            )

            conn.executemany(
                """
                INSERT INTO non_functional_requirements (
                    analysis_id, req_code, category, requirement, priority, metric_target
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        analysis_id,
                        item.req_code,
                        item.category,
                        item.requirement,
                        item.priority,
                        item.metric_target,
                    )
                    for item in record.non_functional_requirements
                ],
            )

            conn.executemany(
                """
                INSERT INTO tech_stack_recommendations (
                    analysis_id, layer, technology, rationale, alternatives_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        analysis_id,
                        item.layer,
                        item.technology,
                        item.rationale,
                        json.dumps(item.alternatives),
                    )
                    for item in record.tech_stack
                ],
            )

            conn.executemany(
                """
                INSERT INTO milestones (
                    analysis_id, phase_number, phase_name, duration_weeks,
                    start_week, end_week, deliverables_json, dependencies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        analysis_id,
                        item.phase_number,
                        item.phase_name,
                        item.duration_weeks,
                        item.start_week,
                        item.end_week,
                        json.dumps(item.deliverables),
                        item.dependencies,
                    )
                    for item in record.milestones
                ],
            )

            conn.executemany(
                """
                INSERT INTO missing_information (
                    analysis_id, area, severity, missing_detail, clarifying_question, impact
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        analysis_id,
                        item.area,
                        item.severity,
                        item.missing_detail,
                        item.clarifying_question,
                        item.impact,
                    )
                    for item in record.missing_information
                ],
            )

            return analysis_id

    def get_analysis(self, analysis_id: int) -> Optional[ProjectAnalysisRecord]:
        """Fetch a single complete ProjectAnalysisRecord by ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
            if not row:
                return None

            fr_rows = conn.execute(
                "SELECT * FROM functional_requirements WHERE analysis_id = ? ORDER BY id ASC",
                (analysis_id,),
            ).fetchall()
            nfr_rows = conn.execute(
                "SELECT * FROM non_functional_requirements WHERE analysis_id = ? ORDER BY id ASC",
                (analysis_id,),
            ).fetchall()
            stack_rows = conn.execute(
                "SELECT * FROM tech_stack_recommendations WHERE analysis_id = ? ORDER BY id ASC",
                (analysis_id,),
            ).fetchall()
            milestone_rows = conn.execute(
                "SELECT * FROM milestones WHERE analysis_id = ? ORDER BY phase_number ASC",
                (analysis_id,),
            ).fetchall()
            gap_rows = conn.execute(
                "SELECT * FROM missing_information WHERE analysis_id = ? ORDER BY id ASC",
                (analysis_id,),
            ).fetchall()

        return ProjectAnalysisRecord(
            id=row["id"],
            project_title=row["project_title"],
            client_name=row["client_name"],
            engagement_type=row["engagement_type"],
            source_type=row["source_type"],
            source_filename=row["source_filename"],
            raw_input_text=row["raw_input_text"],
            executive_summary=row["executive_summary"],
            project_domain=row["project_domain"],
            target_users=json.loads(row["target_users_json"]),
            assumptions=json.loads(row["assumptions_json"]),
            completeness_score=row["completeness_score"],
            readiness_status=row["readiness_status"],
            score_breakdown=CompletenessSummary.model_validate_json(row["score_breakdown_json"]),
            model_used=row["model_used"],
            functional_requirements=[
                FunctionalRequirement(
                    req_code=r["req_code"],
                    title=r["title"],
                    description=r["description"],
                    priority=r["priority"],
                    category=r["category"],
                    acceptance_criteria=r["acceptance_criteria"],
                )
                for r in fr_rows
            ],
            non_functional_requirements=[
                NonFunctionalRequirement(
                    req_code=r["req_code"],
                    category=r["category"],
                    requirement=r["requirement"],
                    priority=r["priority"],
                    metric_target=r["metric_target"],
                )
                for r in nfr_rows
            ],
            tech_stack=[
                TechStackRecommendation(
                    layer=r["layer"],
                    technology=r["technology"],
                    rationale=r["rationale"],
                    alternatives=json.loads(r["alternatives_json"]),
                )
                for r in stack_rows
            ],
            milestones=[
                ProjectMilestone(
                    phase_number=r["phase_number"],
                    phase_name=r["phase_name"],
                    duration_weeks=r["duration_weeks"],
                    start_week=r["start_week"],
                    end_week=r["end_week"],
                    deliverables=json.loads(r["deliverables_json"]),
                    dependencies=r["dependencies"],
                )
                for r in milestone_rows
            ],
            missing_information=[
                MissingInformationItem(
                    area=r["area"],
                    severity=r["severity"],
                    missing_detail=r["missing_detail"],
                    clarifying_question=r["clarifying_question"],
                    impact=r["impact"],
                )
                for r in gap_rows
            ],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_analyses_df(
        self,
        search_query: str = "",
        min_score: float = 0.0,
        readiness_filter: str = "All",
    ) -> pd.DataFrame:
        """Return summary rows of saved analyses as a filtered Pandas DataFrame."""
        query = """
        SELECT
            a.id,
            a.project_title,
            a.client_name,
            a.engagement_type,
            a.project_domain,
            a.source_type,
            a.completeness_score,
            a.readiness_status,
            a.model_used,
            a.created_at,
            (SELECT COUNT(*) FROM functional_requirements fr WHERE fr.analysis_id = a.id) AS fr_count,
            (SELECT COUNT(*) FROM non_functional_requirements nfr WHERE nfr.analysis_id = a.id) AS nfr_count,
            (SELECT COUNT(*) FROM missing_information mi WHERE mi.analysis_id = a.id) AS gap_count,
            (SELECT COALESCE(MAX(m.end_week), 0) FROM milestones m WHERE m.analysis_id = a.id) AS total_weeks
        FROM analyses a
        WHERE a.completeness_score >= ?
        """
        params: List[Any] = [float(min_score)]

        if readiness_filter and readiness_filter != "All":
            query += " AND a.readiness_status = ?"
            params.append(readiness_filter)

        if search_query.strip():
            like_term = f"%{search_query.strip().lower()}%"
            query += (
                " AND (LOWER(a.project_title) LIKE ? OR LOWER(a.client_name) LIKE ? "
                "OR LOWER(a.project_domain) LIKE ?)"
            )
            params.extend([like_term, like_term, like_term])

        query += " ORDER BY a.created_at DESC"

        with self._connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        return df

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Compute aggregate KPI metrics and chart distributions across all analyses."""
        with self._connect() as conn:
            summary_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_analyses,
                    COALESCE(AVG(completeness_score), 0.0) AS avg_completeness,
                    (SELECT COUNT(*) FROM functional_requirements) AS total_frs,
                    (SELECT COUNT(*) FROM non_functional_requirements) AS total_nfrs,
                    (SELECT COUNT(*) FROM missing_information WHERE severity = 'High') AS high_gaps
                FROM analyses
                """
            ).fetchone()

            avg_weeks_row = conn.execute(
                """
                SELECT COALESCE(AVG(project_weeks), 0.0) AS avg_weeks
                FROM (
                    SELECT analysis_id, MAX(end_week) AS project_weeks
                    FROM milestones
                    GROUP BY analysis_id
                )
                """
            ).fetchone()

            fr_priority_df = pd.read_sql_query(
                "SELECT priority, COUNT(*) AS count FROM functional_requirements GROUP BY priority",
                conn,
            )
            nfr_category_df = pd.read_sql_query(
                "SELECT category, COUNT(*) AS count FROM non_functional_requirements GROUP BY category",
                conn,
            )
            readiness_df = pd.read_sql_query(
                "SELECT readiness_status, COUNT(*) AS count FROM analyses GROUP BY readiness_status",
                conn,
            )

        return {
            "total_analyses": int(summary_row["total_analyses"]),
            "avg_completeness": round(float(summary_row["avg_completeness"]), 1),
            "total_frs": int(summary_row["total_frs"]),
            "total_nfrs": int(summary_row["total_nfrs"]),
            "high_gaps": int(summary_row["high_gaps"]),
            "avg_duration_weeks": round(float(avg_weeks_row["avg_weeks"]), 1),
            "fr_priority_df": fr_priority_df,
            "nfr_category_df": nfr_category_df,
            "readiness_df": readiness_df,
        }

    def delete_analysis(self, analysis_id: int) -> bool:
        """Delete an analysis and all cascaded child records."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
            return cursor.rowcount > 0
