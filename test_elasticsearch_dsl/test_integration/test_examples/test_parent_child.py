from datetime import datetime

from pytest import fixture

from elasticsearch_dsl import Q

from .parent_child import User, Question, Answer, setup, Comment

honza = User(id=42, signed_up=datetime(2013, 4, 3), username='honzakral',
            email='honza@elastic.co', localtion='Prague')

nick = User(id=47, signed_up=datetime(2017, 4, 3), username='fxdgear',
            email='nick.lang@elastic.co', localtion='Colorado')


@fixture
def question(write_client):
    setup()
    assert write_client.indices.exists_template(name='base')

    # create a question object
    q = Question(
        _id=1,
        author=nick,
        tags=['elasticsearch', 'python'],
        title='How do I use elasticsearch from Python?',
        body='''
        I want to use elasticsearch, how do I do it from Python?
        ''',
    )
    q.save()
    return q

def test_comment(write_client, question):
    question.add_comment(nick, "Just use elasticsearch-py")

    q = Question.get(1)
    assert isinstance(q, Question)
    assert 1 == len(q.comments)

    c = q.comments[0]
    assert isinstance(c, Comment)
    assert c.author.username == 'fxdgear'


def test_question_answer(write_client, question):
    a = question.add_answer(honza, "Just use `elasticsearch-py`!")

    assert isinstance(a, Answer)

    # refresh the index so we can search right away
    Question._index.refresh()

    # we can now fetch answers from elasticsearch
    answers = question.get_answers()
    assert 1 == len(answers)
    assert isinstance(answers[0], Answer)

    search = Question.search().query('has_child',
        type='answer',
        inner_hits={},
        query=Q('term', author__username__keyword='honzakral'),
    )
    response = search.execute()

    assert 1 == len(response.hits)

    q = response.hits[0]
    assert isinstance(q, Question)
    assert 1 == len(q.meta.inner_hits.answer.hits)
    assert q.meta.inner_hits.answer.hits is q.get_answers()

    a = q.meta.inner_hits.answer.hits[0]
    assert isinstance(a, Answer)
    assert isinstance(a.question, Question)
    assert a.question.meta.id == '1'
