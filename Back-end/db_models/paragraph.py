import sqlalchemy as db
from flask import redirect, url_for
from sqlalchemy.sql.elements import Null
from sqlalchemy.sql.functions import user
from sqlalchemy.orm import backref
from tools.db_tool import make_session, Base, engine
from tools.crypt_tool import app_bcrypt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from tools.string_tools import gettext
from typing import List, Tuple

import time
import re
import datetime


class paragraph_model(Base):
    __tablename__ = "paragraph"
    id = db.Column(db.VARCHAR(250), primary_key=True)
    p_text = db.Column(db.VARCHAR(250), nullable=False)
    ref_book = db.Column(db.VARCHAR(100), nullable=False)

    author = db.Column(db.VARCHAR(200), nullable=False)
    date = db.Column(db.DATETIME, nullable=False)
    replied_id = db.Column(db.VARCHAR(250), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    community_id = db.Column(db.VARCHAR(30), db.ForeignKey("community.id"), nullable=False)
    community_name = db.Column(db.VARCHAR(200), nullable=False)
    tags = db.Column(db.VARCHAR(250), nullable=True)

    impressions = relationship("impressions", backref=backref("paragraph"), lazy="subquery",
                               cascade="all, delete-orphan")
    reply_count = db.Column(db.BIGINT, default=0)
    ima_count = db.Column(db.BIGINT, default=0)

    @property
    def json(self):

        dic = {"id": self.id,
               "p_text": self.p_text,
               "ref_book": self.ref_book,
               "author": self.author,
               "date": str(self.date),
               "replied_id": self.replied_id,
               "user_id": self.user_id,
               "community_id": self.community_id,
               "community_name": self.community_name,
               "tags": self.tags,
               "reply_count": self.reply_count,
               "ima_count": self.ima_count

               }
        return dic

    def __init__(self, user_id, p_text, community_id, community_name, replied_id="", ref_book="", tags="", author=""):
        self.id = community_id + "," + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.p_text = p_text
        self.ref_book = ref_book
        self.user_id = user_id
        self.community_id = community_id
        self.community_name = community_name
        self.date = datetime.datetime.now()
        self.replied_id = replied_id
        self.tags = tags
        self.author = author


def get_user_paragraphs(user_id, engine, start_off=1, end_off=51):
    session = make_session(engine)
    paras: List[paragraph_model] = session.query(paragraph_model).filter(paragraph_model.user_id == user_id) \
        .order_by(paragraph_model.date.desc()).slice(start_off, end_off)
    res = []
    for p in paras:
        res.append(p.json)
    return res


def get_one_paragraph(paragraph_id, engine):
    session = make_session(engine)
    parags: paragraph_model = session.query(paragraph_model).filter(paragraph_model.id == paragraph_id).first()
    return parags


def add_paragraph(text, ref, user_id, community_id, community_name, tags, author, engine):
    session = make_session(engine)
    jwk_user = paragraph_model(p_text=text, ref_book=ref, user_id=user_id, community_id=community_id,
                               community_name=community_name,
                               tags=tags, author=author)
    session.add(jwk_user)
    session.commit()
    return jwk_user.json


def delete_paragraph(p_id, engine):
    session = make_session(engine)
    sesParagraph: paragraph_model = session.query(paragraph_model).filter(paragraph_model.id == p_id).first()
    if sesParagraph.replied_id != "":
        targetParagraph: paragraph_model = session.query(paragraph_model).filter(
            paragraph_model.id == sesParagraph.replied_id).first()
        print("reply_count", targetParagraph.reply_count)
        targetParagraph.reply_count -= 1
    session.delete(sesParagraph)
    session.commit()
    return None


def edit_paragraph(p_id, new_text, new_ref, new_tags, new_author, engine):
    session = make_session(engine)
    parags: paragraph_model = session.query(paragraph_model).filter(paragraph_model.id == p_id).first()
    parags.p_text = new_text

    if new_ref is not None:
        parags.ref_book = new_ref
    if new_author is not None:
        parags.ref_book = new_author
    if new_tags is not None:
        parags.tags = new_tags

    session.flush()
    session.commit()


def get_community_paragraphs(community_id, engine):
    session = make_session(engine)
    parags: paragraph_model = session.query(paragraph_model).filter(paragraph_model.community_id == community_id)
    if parags == None:
        return []
    return parags


def add_reply(user, c_id, p_id, text, engine):
    session = make_session(engine)
    sesParagraph: paragraph_model = session.query(paragraph_model).filter(paragraph_model.id == p_id).first()
    jwk_user = paragraph_model(user_id=user.id, p_text=text, community_id=c_id, replied_id=sesParagraph.id)
    session.add(jwk_user)
    sesParagraph.reply_count += 1

    session.commit()


class POD(Base):
    """
    for saving the paragraph of the day for a community on a specified date
    """
    __tablename__ = "pod"
    id = db.Column(db.VARCHAR(250), primary_key=True)
    c_id = db.Column(db.ForeignKey("community.id", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.VARCHAR(250), nullable=False)
    p_id = db.Column(db.ForeignKey("paragraph.id", ondelete="CASCADE"), nullable=False)
    paragraph = relationship("paragraph_model")

    def __init__(self, date, paragraph: paragraph_model):
        self.id = paragraph.community_id + datetime.datetime.now()
        self.c_id = paragraph.community_id
        self.date = date
        self.paragraph = paragraph

    @property
    def json(self):
        dic = {"id": self.id,
               "c_id": self.c_id,
               "date": str(self.date),
               "paragraph": self.paragraph.json
               }
        return dic


def change_impression(user, p_id, engine):
    """
    :param user:
    :param paragraph:
    :param increment: True for increase impression and False for delete
    :return:
    """
    session = make_session(engine)
    imps: impressions = session.query(impressions).filter(
        db.and_(impressions.u_id == user.id, impressions.p_id == p_id)).first()
    sesParagraph: paragraph_model = session.query(paragraph_model).filter(paragraph_model.id == p_id).first()
    if imps != None:
        session.delete(imps)
        sesParagraph.ima_count -= 1
    else:
        jwk_user = impressions(p_id=p_id, date=datetime.date.today(), u_id=user.id)
        session.add(jwk_user)
        sesParagraph.ima_count += 1

    session.flush()
    session.commit()
    return None


class impressions(Base):
    __tablename__ = "impressions"
    p_id = db.Column(db.VARCHAR(250), db.ForeignKey("paragraph.id", ondelete="CASCADE"), primary_key=True)
    date = db.Column(db.DATE)
    u_id = db.Column(db.ForeignKey("Users.id", ondelete="CASCADE"), primary_key=True)
