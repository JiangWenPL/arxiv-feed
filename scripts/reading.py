#!/usr/bin/env python3
"""CLI for managing reading status — callable by OpenClaw agent.

Usage:
    python scripts/reading.py list [--status unread|reading|done] [--limit N]
    python scripts/reading.py mark <paper_id> <status>
    python scripts/reading.py note <paper_id> <text>
    python scripts/reading.py search <query>
    python scripts/reading.py archive
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.models import init_db, get_db, get_papers, update_reading_status


def cmd_list(args):
    conn = get_db()
    papers = get_papers(conn, status=args.status, limit=args.limit)
    conn.close()
    if not papers:
        print(f"No papers with status '{args.status or 'any'}'.")
        return
    for p in papers:
        status = p.get("status") or "unread"
        score = f"[{p['score']:.0f}]" if p.get("score") else ""
        print(f"  #{p['id']} {score} ({status}) {p['title']}")
        if p.get("notes"):
            print(f"      Note: {p['notes']}")


def cmd_mark(args):
    if args.status not in ("unread", "reading", "done"):
        print(f"Invalid status '{args.status}'. Use: unread, reading, done")
        return
    conn = get_db()
    # Verify paper exists
    row = conn.execute("SELECT id, title FROM papers WHERE id = ?", (args.paper_id,)).fetchone()
    if not row:
        print(f"Paper #{args.paper_id} not found.")
        conn.close()
        return
    update_reading_status(conn, args.paper_id, args.status)
    conn.close()
    print(f"Marked #{args.paper_id} '{row['title'][:60]}' as {args.status}.")


def cmd_note(args):
    conn = get_db()
    row = conn.execute("SELECT id, title FROM papers WHERE id = ?", (args.paper_id,)).fetchone()
    if not row:
        print(f"Paper #{args.paper_id} not found.")
        conn.close()
        return
    note_text = " ".join(args.text)
    update_reading_status(conn, args.paper_id, "reading", notes=note_text)
    conn.close()
    print(f"Added note to #{args.paper_id} '{row['title'][:60]}'.")


def cmd_search(args):
    query = " ".join(args.query).lower()
    conn = get_db()
    papers = get_papers(conn, limit=200)
    conn.close()
    results = [
        p for p in papers
        if query in p["title"].lower() or query in (p.get("abstract") or "").lower()
    ]
    if not results:
        print(f"No papers matching '{query}'.")
        return
    print(f"Found {len(results)} papers matching '{query}':")
    for p in results[:20]:
        status = p.get("status") or "unread"
        score = f"[{p['score']:.0f}]" if p.get("score") else ""
        print(f"  #{p['id']} {score} ({status}) {p['title']}")


def cmd_archive(args):
    conn = get_db()
    done = get_papers(conn, status="done", limit=500)
    if not done:
        print("No papers with status 'done' to archive.")
        conn.close()
        return
    for p in done:
        conn.execute(
            "UPDATE reading_status SET archived_at = datetime('now') WHERE paper_id = ?",
            (p["id"],),
        )
    conn.commit()
    conn.close()
    print(f"Archived {len(done)} finished papers.")


def main():
    parser = argparse.ArgumentParser(description="Manage reading status")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="List papers by status")
    p_list.add_argument("--status", default="unread", help="Filter: unread|reading|done")
    p_list.add_argument("--limit", type=int, default=20)

    p_mark = sub.add_parser("mark", help="Mark a paper's reading status")
    p_mark.add_argument("paper_id", type=int)
    p_mark.add_argument("status", help="unread|reading|done")

    p_note = sub.add_parser("note", help="Add a note to a paper")
    p_note.add_argument("paper_id", type=int)
    p_note.add_argument("text", nargs="+")

    p_search = sub.add_parser("search", help="Search papers by title/abstract")
    p_search.add_argument("query", nargs="+")

    sub.add_parser("archive", help="Archive all done papers")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    init_db()
    {"list": cmd_list, "mark": cmd_mark, "note": cmd_note,
     "search": cmd_search, "archive": cmd_archive}[args.command](args)


if __name__ == "__main__":
    main()
