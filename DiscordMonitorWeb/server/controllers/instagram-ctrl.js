const { InstagramModel } = require('../model')

let getInstagramPosts = async (req, res) => {
    let page = req.body.page
    let size = req.body.size
    let type = req.body.type
    let keyword = req.body.keyword
    let username = req.body.username

    let match
    let query
    if (size < 1) {
        size = 21
    }
    if (page > 100) {
        page = 100
    }
    if (keyword) {
        if (type) {
            match = [{
                $match: {
                    $text: {
                        $search: keyword
                    },
                    "type": type
                }
            }, {
                $sort: {
                    "score": {
                        $meta: "textScore"
                    },
                    post_time: - 1
                }
            }]
        } else {
            match = [{
                $match: {
                    $text: {
                        $search: keyword
                    }
                }
            },
            {
                $sort: {
                    "score": {
                        $meta: "textScore"
                    },
                    post_time: - 1
                }
            }]
        }
    } else {
        if (type) {
            match = [{
                $match: {
                    "type": type
                }
            },
            {
                $sort: {
                    post_time: - 1
                }
            }]
        }
    }
    let query2 =
        [
            {
                $skip: page * size
            },
            {
                $limit: size
            }
        ]

    if (match) {
        query = [...match, ...query2]
    } else {
        query =
            [
                {
                    $sort: {
                        post_time: - 1
                    }
                },
                {
                    $skip: page * size
                },
                {
                    $limit: size
                }
            ]
    }
    await InstagramModel.aggregate(query)
        .exec((err, products) => {
            if (err) {
                console.error(err)
                return res.status(400).json({ success: false, error: err })
            }
            return res.status(200).json({ success: true, data: products })

        })
}


module.exports = {
    getInstagramPosts
}