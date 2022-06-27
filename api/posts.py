from flask import jsonify, request, g, abort

from api import api
from db.shared import db

from db.models.user_post import UserPost
from db.models.post import Post
from db.models.user import User

from db.utils import row_to_dict, rows_to_list
from middlewares import auth_required

from api.statics import *
import re


@api.post("/posts")
@auth_required
def posts():
    # validation
    user = g.get("user")
    if user is None:
        return abort(401)

    data = request.get_json(force=True)
    text = data.get("text", None)
    tags = data.get("tags", None)
    if text is None:
        return jsonify({"error": "Must provide text for the new post"}), 400

    # Create new post
    post_values = {"text": text}
    if tags:
        post_values["tags"] = tags

    post = Post(**post_values)
    db.session.add(post)
    db.session.commit()

    user_post = UserPost(user_id=user.id, post_id=post.id)
    db.session.add(user_post)
    db.session.commit()

    return row_to_dict(post), 200


@api.get("/posts")
@auth_required
def get_posts():

    user = g.get("user")
    if user is None:
        return abort(401)

    author_ids = request.args.get("authorIds")
    sort_method = request.args.get("sortBy")
    direction = request.args.get("direction")

    if author_ids is None:
        return jsonify({"error": "Must provide at least one author id"}), 400
    if not isinstance(author_ids, str):
        return jsonify({"error": "invalid type. authorIds must be a string"}), 400

    if direction is not None:
        if not isinstance(direction, str):
            return jsonify({"error": "invalid type. sortBy must be a string"}), 400
        if direction not in Direction.__members__:
            return (
                jsonify(
                    {
                        "error": "The only acceptable values for direction are: asc or desc "
                    }
                ),
                400,
            )

    if sort_method is not None:
        if not isinstance(sort_method, str):
            return jsonify({"error": "invalid type. direction must be a string"}), 400
        if sort_method not in Sorting.__members__:
            return (
                jsonify(
                    {
                        "error": "The only acceptable values for sortBy are: id, reads , likes and popularity"
                    }
                ),
                400,
            )

    if re.match("^[0-9]+(,[0-9]+)*$", author_ids) is None:
        return (
            jsonify(
                {
                    "error": "authorIds must be a comma separated list of integer user IDs."
                }
            ),
            400,
        )

    ids = author_ids.split(",")
    query = db.session.query(Post).join(UserPost).filter(UserPost.user_id.in_(ids))

    match direction:
        case Direction.desc.name:
            if sort_method:
                query = query.order_by(getattr(Post, sort_method).desc())
            else:
                query = query.order_by(Post.id.desc())
        case Direction.asc.name:
            if sort_method:
                query = query.order_by(getattr(Post, sort_method).asc())
            else:
                query.order_by(Post.id.asc())
        case _:
            if sort_method:
                query = query.order_by(getattr(Post, sort_method))
            else:
                query = query.order_by(Post.id)

    res = {"posts": rows_to_list(query.all())}
    return jsonify(res), 200


@api.patch("/posts/<int:postId>")
@auth_required
def update_post(postId):

    data = request.get_json(force=True)

    author_ids = data.get("authorIds", None)
    tags = data.get("tags", None)
    text = data.get("text", None)

    post_values = {}
    if author_ids:
        post_values["authorIds"] = author_ids
    if tags:
        post_values["tags"] = tags
    if text:
        post_values["text"] = text

    if post_values:

        post = Post.query.filter(Post.id == postId).one()
        if "tags" in post_values:
            post.tags = post_values["tags"]

        if "text" in post_values:
            post.text = post_values["text"]

        if "authorIds" in post_values:
            UserPost.query.filter(UserPost.post_id == postId).delete()
            for id in post_values["authorIds"]:
                user_post = UserPost(user_id=id, post_id=postId)
                if User.query.filter(User.id == id).scalar() is not None:
                    db.session.add(user_post)

                else:
                    return (
                        jsonify(
                            {"error": "Cannot add non-existent users to authorIds"}
                        ),
                        400,
                    )

        db.session.commit()
        updated_post = row_to_dict(Post.query.get(postId))
        updated_ids = [
            user.user_id
            for user in UserPost.query.filter(UserPost.post_id == postId).all()
        ]
        updated_post["authorIds"] = updated_ids
        res = {"post": updated_post}
        return jsonify(res), 200

    else:
        post = Post.query.get(postId)
        res = row_to_dict(post)
        return res, 200

    return jsonify({"message": postId}), 200
