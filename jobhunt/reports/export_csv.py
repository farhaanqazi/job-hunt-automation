import csv
from io import StringIO

CSV_FIELDNAMES = [
    "id",
    "fit_score",
    "remote_category",
    "company",
    "title",
    "source_id",
    "source_url",
    "attribution",
    "status",
]


def rows_to_csv_text(rows) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "id": row.id,
                "fit_score": row.fit_score,
                "remote_category": row.remote_category,
                "company": row.company,
                "title": row.title,
                "source_id": row.source_id,
                "source_url": row.source_url,
                "attribution": row.attribution,
                "status": row.status,
            }
        )
    return output.getvalue()
