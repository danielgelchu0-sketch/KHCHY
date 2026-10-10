from django.db import migrations


def consolidate_topics(apps, schema_editor):
    Topic = apps.get_model('discussions', 'Topic')
    Discussion = apps.get_model('discussions', 'Discussion')

    # 1. Create or get "Youth & Emotional Well-being"
    youth_topic, _ = Topic.objects.get_or_create(
        slug='youth-emotional-wellbeing',
        defaults={
            'name': 'Youth & Emotional Well-being',
            'description': 'A dedicated, safe room for teens, youths, and young adults tackling peer pressure, identity, emotional struggles, anxiety, burnout, and life choices.',
            'icon': 'heart',
            'order': 2,
        }
    )

    # 2. Create or get "Relationships, Marriage & Boundaries"
    relationships_topic, _ = Topic.objects.get_or_create(
        slug='relationships-marriage-boundaries',
        defaults={
            'name': 'Relationships, Marriage & Boundaries',
            'description': 'Biblical dialogue on godly dating, purity, healthy boundaries, temptations, courtship, marriage communication, and Christian family life.',
            'icon': 'user-group',
            'order': 3,
        }
    )

    # 3. Migrate discussions from old youth & mental health topics
    Discussion.objects.filter(topic__slug__in=['youth-questions', 'mental-emotional-struggles']).update(topic=youth_topic)

    # 4. Migrate discussions from old relationship, sexuality, and marriage topics
    Discussion.objects.filter(topic__slug__in=['sexuality-boundaries', 'relationships-dating', 'marriage-family']).update(topic=relationships_topic)

    # 5. Remove the old deprecated topics
    Topic.objects.filter(slug__in=[
        'youth-questions',
        'mental-emotional-struggles',
        'sexuality-boundaries',
        'relationships-dating',
        'marriage-family'
    ]).delete()

    # 6. Re-order remaining topics sequentially
    orders = {
        'faith-spiritual-life': 1,
        'youth-emotional-wellbeing': 2,
        'relationships-marriage-boundaries': 3,
        'bible-questions-theology': 4,
        'education-career': 5,
        'church-life-community': 6,
        'general-discussion': 7,
    }
    for slug, order_num in orders.items():
        Topic.objects.filter(slug=slug).update(order=order_num)


def reverse_consolidation(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('discussions', '0003_replyreaction'),
    ]

    operations = [
        migrations.RunPython(consolidate_topics, reverse_consolidation),
    ]
