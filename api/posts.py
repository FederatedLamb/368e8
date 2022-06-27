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
    sort_method = request.args.get("sortBy", "id")
    direction = request.args.get("direction", "asc")

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

    query = query.order_by(getattr(getattr(Post, sort_method), direction)())

    posts = rows_to_list(query.all())

    res = {"posts": posts}
    return jsonify(res), 200



@api.patch("/posts/<int:postId>")
@auth_required
def update_post(postId):

    user = g.get("user")
    if user is None:
        return abort(401)

    data = request.get_json(force=True)

    author_ids = data.get("authorIds", None)
    tags = data.get("tags", None)
    text = data.get("text", None)

    if isinstance(author_ids, list):
        for id in author_ids:
            if not isinstance(id, int):
                return jsonify({"error": "authorIds must be an array of Ints"}), 400
    elif author_ids is not None:
        return (
            jsonify({"error": "Invalid type: authorIds must be an array of Ints"}),
            400,
        )

    if isinstance(tags, list):
        for tag in tags:
            if not isinstance(tag, str):
                return jsonify({"error": "tags must be an array of strings"}), 400
    elif tags is not None:
        return jsonify({"error": "Invalid type: tags must be an array of strings"}), 400

    if text is not None and not isinstance(text, str):
        return jsonify({"error": "text must be a string"}), 400

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

    post = Post.query.get(postId)
    res = row_to_dict(post)
    updated_ids = [
        user.user_id
        for user in UserPost.query.filter(UserPost.post_id == postId).all()
    ]
    res["authorIds"] = updated_ids
    return jsonify(res), 200
