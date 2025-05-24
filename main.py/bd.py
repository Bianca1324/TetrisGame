import sqlite3

def delete_bianca_scores():
    with sqlite3.connect("tetris.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scoruri WHERE LOWER(nume) = ?", ("denisa",))
        conn.commit()
        print("Scorurile pentru 'denisa' au fost șterse.")

delete_bianca_scores()
