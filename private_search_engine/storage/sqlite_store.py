import sqlite3
from pathlib import Path
from ..core.document import Document
class SQLiteStore:
    """Persistent document metadata store for incremental crawling."""
    def __init__(self,path='data/search.db'):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self._init()
    def _connect(self): con=sqlite3.connect(self.path);con.row_factory=sqlite3.Row;return con
    def _init(self):
        with self._connect() as con:
            con.execute('''CREATE TABLE IF NOT EXISTS documents (doc_id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, title TEXT NOT NULL, text TEXT NOT NULL, content_type TEXT NOT NULL, etag TEXT, last_modified TEXT, content_hash TEXT NOT NULL, fetched_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active')''');con.execute('CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url)');con.execute('CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash)')
    def upsert(self,doc,*,etag=None,last_modified=None,content_hash=None,fetched_at=None):
        import datetime
        content_hash=content_hash or doc.content_hash;fetched_at=fetched_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._connect() as con:
            con.execute('''INSERT INTO documents (doc_id,url,title,text,content_type,etag,last_modified,content_hash,fetched_at,status) VALUES (?,?,?,?,?,?,?,?,?,'active') ON CONFLICT(doc_id) DO UPDATE SET url=excluded.url,title=excluded.title,text=excluded.text,content_type=excluded.content_type,etag=excluded.etag,last_modified=excluded.last_modified,content_hash=excluded.content_hash,fetched_at=excluded.fetched_at,status='active' ''',(doc.doc_id,doc.url,doc.title,doc.text,doc.content_type,etag,last_modified,content_hash,fetched_at))
    def get_by_url(self,url):
        with self._connect() as con:
            row=con.execute('SELECT * FROM documents WHERE url=?',(url,)).fetchone();return dict(row) if row else None
    def all_documents(self):
        with self._connect() as con:
            rows=con.execute("SELECT * FROM documents WHERE status='active' ORDER BY url").fetchall();return [Document(r['url'],r['title'],r['text'],r['content_type']) for r in rows]
    def count(self):
        with self._connect() as con:return con.execute("SELECT COUNT(*) FROM documents WHERE status='active'").fetchone()[0]
