"""Small classroom workspace for local pilots; institutional auth remains external."""
from __future__ import annotations

import secrets
import sqlite3
from datetime import date, datetime, timezone
from uuid import uuid4

from materia import store


def migrate() -> None:
    with store.connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS courses (
            id TEXT PRIMARY KEY, owner TEXT NOT NULL, title TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE, description TEXT NOT NULL, created TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS course_members (
            course_id TEXT NOT NULL, owner TEXT NOT NULL, display_name TEXT NOT NULL,
            joined TEXT NOT NULL, PRIMARY KEY(course_id,owner),
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS assignments (
            id TEXT PRIMARY KEY, course_id TEXT NOT NULL, owner TEXT NOT NULL,
            title TEXT NOT NULL, instructions TEXT NOT NULL, due_date TEXT,
            pathway TEXT NOT NULL, created TEXT NOT NULL,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY, assignment_id TEXT NOT NULL, owner TEXT NOT NULL,
            display_name TEXT NOT NULL, simulation_id TEXT NOT NULL, note TEXT NOT NULL,
            status TEXT NOT NULL, submitted TEXT NOT NULL, grade REAL,
            feedback TEXT, reviewed_at TEXT,
            FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
            UNIQUE(assignment_id,owner)
        );
        CREATE INDEX IF NOT EXISTS idx_course_members_owner ON course_members(owner,joined DESC);
        CREATE INDEX IF NOT EXISTS idx_assignments_course ON assignments(course_id,created DESC);
        CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id,submitted DESC);
        """)
        submission_columns={row['name'] for row in conn.execute('PRAGMA table_info(submissions)')}
        for name,kind in {'grade':'REAL','feedback':'TEXT','reviewed_at':'TEXT'}.items():
            if name not in submission_columns:
                conn.execute(f'ALTER TABLE submissions ADD COLUMN {name} {kind}')
        conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_course(owner: str, title: str, description: str = '', *, authorized_teacher: bool = False) -> dict:
    migrate(); title=title.strip(); description=description.strip()
    if not authorized_teacher:
        raise PermissionError('Un compte enseignant ou administrateur est requis pour créer un cours.')
    if not owner or len(title)<3:
        raise ValueError('Le nom du cours doit contenir au moins 3 caractères.')
    ident=str(uuid4())
    with store.connect() as conn:
        for _ in range(20):
            code=secrets.token_hex(3).upper()
            try:
                conn.execute('INSERT INTO courses VALUES (?,?,?,?,?,?)',
                             (ident,owner,title[:160],code,description[:2000],_now()))
                conn.commit(); break
            except sqlite3.IntegrityError:
                continue
        else:
            raise RuntimeError('Impossible de générer un code de cours unique.')
    return course(ident,owner)


def transfer_owner(source_owner: str, target_owner: str, *, include_teacher_content: bool = False) -> int:
    """Move guest classroom work to a fresh authenticated identity."""
    migrate()
    if not source_owner or not target_owner or source_owner == target_owner:
        return 0
    changed=0
    with store.connect() as conn:
        tables=['course_members','submissions']
        if include_teacher_content:
            tables[:0]=['courses','assignments']
        for table in tables:
            cursor=conn.execute(f'UPDATE {table} SET owner=? WHERE owner=?',(target_owner,source_owner))
            changed+=int(cursor.rowcount)
        conn.commit()
    return changed


def join_course(owner: str, code: str, display_name: str) -> dict:
    migrate(); code=code.strip().upper(); display_name=display_name.strip()
    if not owner or len(display_name)<2:
        raise ValueError('Indiquez votre nom ou identifiant étudiant.')
    with store.connect() as conn:
        row=conn.execute('SELECT * FROM courses WHERE code=?',(code,)).fetchone()
        if not row:
            raise ValueError('Code de cours inconnu.')
        if row['owner']==owner:
            raise ValueError('Vous êtes déjà responsable de ce cours.')
        conn.execute('''INSERT INTO course_members(course_id,owner,display_name,joined)
            VALUES (?,?,?,?) ON CONFLICT(course_id,owner) DO UPDATE SET display_name=excluded.display_name''',
            (row['id'],owner,display_name[:160],_now()))
        conn.commit()
    return course(row['id'],owner)


def courses_for_owner(owner: str) -> list[dict]:
    migrate()
    with store.connect() as conn:
        rows=conn.execute('''SELECT c.*,'teacher' role,NULL display_name FROM courses c WHERE c.owner=?
            UNION ALL
            SELECT c.*,'student' role,m.display_name FROM courses c
            JOIN course_members m ON m.course_id=c.id WHERE m.owner=?
            ORDER BY created DESC''',(owner,owner)).fetchall()
    return [dict(row) for row in rows]


def course(course_id: str, owner: str) -> dict | None:
    return next((item for item in courses_for_owner(owner) if item['id']==course_id),None)


def create_assignment(owner: str, course_id: str, title: str, instructions: str,
                      pathway: str, due_date: str | None = None) -> dict:
    migrate(); title=title.strip(); instructions=instructions.strip(); due_date=(due_date or '').strip() or None
    if pathway not in {'estimation','published','guided'}:
        raise ValueError('Parcours de travail inconnu.')
    if len(title)<3 or len(instructions)<10:
        raise ValueError('Ajoutez un titre et une consigne d’au moins 10 caractères.')
    if due_date:
        try: due_date=date.fromisoformat(due_date).isoformat()
        except ValueError as exc: raise ValueError('La date limite doit suivre le format AAAA-MM-JJ.') from exc
    with store.connect() as conn:
        target=conn.execute('SELECT * FROM courses WHERE id=? AND owner=?',(course_id,owner)).fetchone()
        if not target:
            raise PermissionError('Seul le responsable du cours peut publier un travail.')
        ident=str(uuid4())
        conn.execute('INSERT INTO assignments VALUES (?,?,?,?,?,?,?,?)',
                     (ident,course_id,owner,title[:200],instructions[:4000],due_date,pathway,_now()))
        conn.commit()
    return next(a for a in assignments(course_id) if a['id']==ident)


def assignments(course_id: str) -> list[dict]:
    migrate()
    with store.connect() as conn:
        rows=conn.execute('SELECT * FROM assignments WHERE course_id=? ORDER BY created DESC',(course_id,)).fetchall()
    return [dict(row) for row in rows]


def duplicate_assignment(owner: str, assignment_id: str, due_date: str | None = None) -> dict:
    migrate()
    with store.connect() as conn:
        source=conn.execute('''SELECT a.* FROM assignments a JOIN courses c ON c.id=a.course_id
            WHERE a.id=? AND c.owner=?''',(assignment_id,owner)).fetchone()
    if not source:
        raise PermissionError('Seul le responsable du cours peut dupliquer ce travail.')
    return create_assignment(owner,source['course_id'],'Copie de '+source['title'],source['instructions'],
                             source['pathway'],due_date)


def course_stats(owner: str, course_id: str) -> dict:
    migrate()
    with store.connect() as conn:
        target=conn.execute('SELECT id FROM courses WHERE id=? AND owner=?',(course_id,owner)).fetchone()
        if not target:
            raise PermissionError('Seul le responsable du cours peut consulter ce tableau de bord.')
        members=conn.execute('SELECT COUNT(*) FROM course_members WHERE course_id=?',(course_id,)).fetchone()[0]
        assignments_count=conn.execute('SELECT COUNT(*) FROM assignments WHERE course_id=?',(course_id,)).fetchone()[0]
        submissions_count=conn.execute('''SELECT COUNT(*) FROM submissions s JOIN assignments a ON a.id=s.assignment_id
            WHERE a.course_id=?''',(course_id,)).fetchone()[0]
        reviewed=conn.execute('''SELECT COUNT(*) FROM submissions s JOIN assignments a ON a.id=s.assignment_id
            WHERE a.course_id=? AND s.status='reviewed' ''',(course_id,)).fetchone()[0]
        average=conn.execute('''SELECT AVG(s.grade) FROM submissions s JOIN assignments a ON a.id=s.assignment_id
            WHERE a.course_id=? AND s.grade IS NOT NULL''',(course_id,)).fetchone()[0]
    return {'students':int(members),'assignments':int(assignments_count),'submissions':int(submissions_count),
            'reviewed':int(reviewed),'pending_review':int(submissions_count-reviewed),
            'average_grade':float(average) if average is not None else None}


def submit(owner: str, assignment_id: str, simulation_id: str, display_name: str, note: str = '') -> dict:
    migrate(); display_name=display_name.strip(); note=note.strip()
    if len(display_name)<2:
        raise ValueError('Indiquez votre nom ou identifiant étudiant.')
    simulation=store.get(owner,simulation_id)
    if not simulation or simulation['kind']!='simulation':
        raise ValueError('Choisissez une simulation enregistrée dans votre espace.')
    with store.connect() as conn:
        assignment=conn.execute('SELECT * FROM assignments WHERE id=?',(assignment_id,)).fetchone()
        if not assignment:
            raise ValueError('Travail inconnu.')
        member=conn.execute('SELECT * FROM course_members WHERE course_id=? AND owner=?',
                            (assignment['course_id'],owner)).fetchone()
        if not member:
            raise PermissionError('Vous ne faites pas partie de ce cours.')
        existing=conn.execute('SELECT id FROM submissions WHERE assignment_id=? AND owner=?',
                              (assignment_id,owner)).fetchone()
        ident=existing['id'] if existing else str(uuid4())
        conn.execute('''INSERT INTO submissions(id,assignment_id,owner,display_name,simulation_id,note,status,submitted,grade,feedback,reviewed_at)
            VALUES (?,?,?,?,?,?,'submitted',?,NULL,NULL,NULL) ON CONFLICT(assignment_id,owner) DO UPDATE SET
            display_name=excluded.display_name,simulation_id=excluded.simulation_id,note=excluded.note,
            status=excluded.status,submitted=excluded.submitted,grade=NULL,feedback=NULL,reviewed_at=NULL''',
            (ident,assignment_id,owner,display_name[:160],simulation_id,note[:2000],_now()))
        conn.commit()
    return {'id':ident,'status':'submitted'}


def submissions(owner: str, course_id: str) -> list[dict]:
    migrate()
    with store.connect() as conn:
        target=conn.execute('SELECT id FROM courses WHERE id=? AND owner=?',(course_id,owner)).fetchone()
        if not target:
            raise PermissionError('Seul le responsable du cours peut consulter les remises.')
        rows=conn.execute('''SELECT s.*,a.title assignment_title,r.name simulation_name,r.payload simulation_payload
            FROM submissions s JOIN assignments a ON a.id=s.assignment_id
            JOIN records r ON r.id=s.simulation_id WHERE a.course_id=? ORDER BY s.submitted DESC''',(course_id,)).fetchall()
    return [dict(row) for row in rows]


def student_submissions(owner: str, course_id: str) -> list[dict]:
    migrate()
    with store.connect() as conn:
        member=conn.execute('SELECT 1 FROM course_members WHERE course_id=? AND owner=?',(course_id,owner)).fetchone()
        if not member:
            raise PermissionError('Vous ne faites pas partie de ce cours.')
        rows=conn.execute('''SELECT s.*,a.title assignment_title,r.name simulation_name
            FROM submissions s JOIN assignments a ON a.id=s.assignment_id
            JOIN records r ON r.id=s.simulation_id
            WHERE a.course_id=? AND s.owner=? ORDER BY s.submitted DESC''',(course_id,owner)).fetchall()
    return [dict(row) for row in rows]


def review_submission(owner: str, submission_id: str, grade: float | None, feedback: str) -> dict:
    migrate(); feedback=feedback.strip()
    if grade is not None and not 0<=float(grade)<=20:
        raise ValueError('La note doit être comprise entre 0 et 20.')
    if len(feedback)<3:
        raise ValueError('Ajoutez un retour d’au moins 3 caractères.')
    with store.connect() as conn:
        row=conn.execute('''SELECT s.id FROM submissions s
            JOIN assignments a ON a.id=s.assignment_id JOIN courses c ON c.id=a.course_id
            WHERE s.id=? AND c.owner=?''',(submission_id,owner)).fetchone()
        if not row:
            raise PermissionError('Seul le responsable du cours peut corriger cette remise.')
        reviewed=_now()
        conn.execute("UPDATE submissions SET grade=?,feedback=?,reviewed_at=?,status='reviewed' WHERE id=?",
                     (float(grade) if grade is not None else None,feedback[:4000],reviewed,submission_id))
        conn.commit()
    return {'id':submission_id,'status':'reviewed','grade':float(grade) if grade is not None else None,
            'feedback':feedback,'reviewed_at':reviewed}
