from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("Farmers", "0013_fix_userprofile_user_fk"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
PRAGMA foreign_keys = OFF;

CREATE TABLE "new__Farmers_userprofile" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "role" varchar(20) NOT NULL,
    "is_approved" bool NOT NULL,
    "user_id" bigint NOT NULL UNIQUE REFERENCES "Farmers_farmer" ("id") DEFERRABLE INITIALLY DEFERRED,
    "created_by_agent_id" bigint NULL REFERENCES "Farmers_farmer" ("id") DEFERRABLE INITIALLY DEFERRED
);

INSERT INTO "new__Farmers_userprofile" ("id", "role", "is_approved", "user_id", "created_by_agent_id")
SELECT up."id", up."role", up."is_approved", up."user_id", up."created_by_agent_id"
FROM "Farmers_userprofile" up
INNER JOIN "Farmers_farmer" f ON f."id" = up."user_id"
LEFT JOIN "Farmers_farmer" ca ON ca."id" = up."created_by_agent_id"
WHERE up."created_by_agent_id" IS NULL OR ca."id" IS NOT NULL;

DROP TABLE "Farmers_userprofile";
ALTER TABLE "new__Farmers_userprofile" RENAME TO "Farmers_userprofile";
CREATE INDEX "Farmers_userprofile_created_by_agent_id_d278e24c" ON "Farmers_userprofile" ("created_by_agent_id");

PRAGMA foreign_keys = ON;
""",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
