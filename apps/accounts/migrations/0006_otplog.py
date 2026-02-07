from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_alter_accountprofile_phone_onboardingprofile_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OTPLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("identifier", models.CharField(db_index=True, max_length=254)),
                ("channel", models.CharField(choices=[("email", "Email"), ("sms", "SMS")], max_length=20)),
                (
                    "code_type",
                    models.CharField(choices=[("REAL", "Real"), ("TEST", "Test")], max_length=10),
                ),
                ("verified_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["identifier", "verified_at"], name="otp_log_ident_time_idx"),
                    models.Index(fields=["channel", "verified_at"], name="otp_log_channel_time_idx"),
                ],
            },
        ),
    ]
