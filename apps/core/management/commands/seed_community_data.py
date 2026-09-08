from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.discussions.models import Discussion, Reply, Topic


class Command(BaseCommand):
    help = "Seeds initial church community discussion topics, default roles, and sample data."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding HKHC community platform data..."))

        # 1. Create Topics
        topics_data = [
            {
                "name": "Faith & Spiritual Life",
                "slug": "faith-spiritual-life",
                "description": "Questions about prayer, spiritual doubts, personal devotion, hearing God's voice, and growing in Christ.",
                "icon": "cross",
                "order": 1,
            },
            {
                "name": "Youth Questions",
                "slug": "youth-questions",
                "description": "A dedicated, supportive room for teens, youths, and young adults tackling peer pressure, identity, and life choices.",
                "icon": "academic-cap",
                "order": 2,
            },
            {
                "name": "Mental & Emotional Struggles",
                "slug": "mental-emotional-struggles",
                "description": "Safe, compassionate discussions regarding anxiety, depression, burnout, grief, loneliness, and emotional well-being.",
                "icon": "heart",
                "order": 3,
            },
            {
                "name": "Sexuality & Boundaries",
                "slug": "sexuality-boundaries",
                "description": "Confidential, biblical, and sensitive dialogue on purity, dating boundaries, temptations, attraction, and healing.",
                "icon": "shield-check",
                "order": 4,
            },
            {
                "name": "Relationships & Dating",
                "slug": "relationships-dating",
                "description": "Navigating friendships, godly dating, courtship, heartbreaks, and healthy relationship patterns.",
                "icon": "user-group",
                "order": 5,
            },
            {
                "name": "Marriage & Family",
                "slug": "marriage-family",
                "description": "Couples, parents, and families discussing marriage challenges, parenting, communication, and home life.",
                "icon": "home",
                "order": 6,
            },
            {
                "name": "Bible Questions & Theology",
                "slug": "bible-questions-theology",
                "description": "Scripture interpretation, difficult biblical passages, theology questions, and apologetics.",
                "icon": "book-open",
                "order": 7,
            },
            {
                "name": "Education & Career",
                "slug": "education-career",
                "description": "School, college decisions, workplace integrity, career discernment, and balancing work with Christian faith.",
                "icon": "briefcase",
                "order": 8,
            },
            {
                "name": "Church Life & Community",
                "slug": "church-life-community",
                "description": "Ministry involvement, serving in church, resolving interpersonal friction, and building authentic community fellowship.",
                "icon": "building-office",
                "order": 9,
            },
            {
                "name": "General Discussion",
                "slug": "general-discussion",
                "description": "Open fellowship, encouraging testimonies, books, hobbies, and everyday community conversations.",
                "icon": "chat-bubble",
                "order": 10,
            },
        ]

        created_topics = {}
        for t_info in topics_data:
            topic, created = Topic.objects.get_or_create(
                slug=t_info["slug"],
                defaults={
                    "name": t_info["name"],
                    "description": t_info["description"],
                    "icon": t_info["icon"],
                    "order": t_info["order"],
                },
            )
            created_topics[topic.slug] = topic
            status = "Created" if created else "Already exists"
            self.stdout.write(f"  Topic: '{topic.name}' ({status})")

        # 2. Create Users
        admin_user, admin_created = User.objects.get_or_create(
            email="admin@hkhc.org",
            defaults={
                "display_name": "Pastor Andrew (Admin)",
                "role": User.Role.ADMINISTRATOR,
                "is_staff": True,
                "is_superuser": True,
                "status": User.AccountStatus.ACTIVE,
            },
        )
        if admin_created:
            admin_user.set_password("AdminPass123!")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("  Admin created: admin@hkhc.org / AdminPass123!"))

        mod_user, mod_created = User.objects.get_or_create(
            email="moderator@hkhc.org",
            defaults={
                "display_name": "Deaconess Ruth (Moderator)",
                "role": User.Role.MODERATOR,
                "is_staff": True,
                "status": User.AccountStatus.ACTIVE,
            },
        )
        if mod_created:
            mod_user.set_password("ModeratorPass123!")
            mod_user.save()
            self.stdout.write(self.style.SUCCESS("  Moderator created: moderator@hkhc.org / ModeratorPass123!"))

        youth_user, youth_created = User.objects.get_or_create(
            email="daniel@example.com",
            defaults={
                "display_name": "Daniel K.",
                "role": User.Role.MEMBER,
                "status": User.AccountStatus.ACTIVE,
            },
        )
        if youth_created:
            youth_user.set_password("MemberPass123!")
            youth_user.save()
            self.stdout.write("  Member created: daniel@example.com / MemberPass123!")

        sarah_user, sarah_created = User.objects.get_or_create(
            email="sarah@example.com",
            defaults={
                "display_name": "Sarah M.",
                "role": User.Role.MEMBER,
                "status": User.AccountStatus.ACTIVE,
            },
        )
        if sarah_created:
            sarah_user.set_password("MemberPass123!")
            sarah_user.save()
            self.stdout.write("  Member created: sarah@example.com / MemberPass123!")

        # 3. Seed Sample Discussion (Demonstrating Anonymous Posting)
        mental_health_topic = created_topics.get("mental-emotional-struggles")
        if mental_health_topic and not Discussion.objects.filter(topic=mental_health_topic).exists():
            disc1 = Discussion.objects.create(
                topic=mental_health_topic,
                author=daniel_user if 'daniel_user' in locals() else youth_user,
                title="How do I overcome persistent anxiety when everyone at church expects me to be joyful?",
                content=(
                    "<p>I have been struggling deeply with severe panic attacks and anxiety over the last few months. "
                    "In our youth gatherings, it often feels like having faith means you should never feel afraid or sad. "
                    "I am terrified of admitting this to my friends because I don't want people to think I am lacking faith. "
                    "How do biblically grounded believers navigate professional counseling alongside prayer?</p>"
                ),
                is_anonymous=True,  # Posted anonymously!
                status=Discussion.Status.ACTIVE,
                last_activity_at=timezone.now(),
            )
            # Add an identified answer
            reply1 = Reply.objects.create(
                discussion=disc1,
                author=sarah_user,
                content=(
                    "<p>Thank you so much for asking this. You are NOT alone, and feeling anxious is never proof of a broken faith. "
                    "Remember that Elijah, David in the Psalms, and even Jesus in the Garden experienced deep emotional anguish. "
                    "Seeking medical care or licensed Christian counseling is just like visiting a doctor for a physical illness—God works through doctors and therapists too!</p>"
                ),
                is_anonymous=False,  # Posted identified
                status=Reply.Status.ACTIVE,
            )
            # Add a nested reply
            Reply.objects.create(
                discussion=disc1,
                parent=reply1,
                author=youth_user,
                content=(
                    "<p>Thank you Sarah, this brings so much relief. "
                    "Do you have any recommendations on how to bring this up to parents without alarming them?</p>"
                ),
                is_anonymous=True,  # Nested reply also posted anonymously!
                status=Reply.Status.ACTIVE,
            )
            self.stdout.write(self.style.SUCCESS("  Sample anonymous discussion and replies seeded successfully."))

        self.stdout.write(self.style.SUCCESS("Database seeding complete!"))
