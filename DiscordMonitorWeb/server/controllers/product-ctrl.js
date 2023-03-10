const { ProductModel } = require('../model')

let getProducts = async (req, res) => {
    let keyword = req.body.q
    let shoeSize = req.body.s
    let match_query = shoeSize.length > 0 ? 
    [ {
        $match: {
            $text: {
                $search: keyword
            },
            "prod_size": {
                $in: shoeSize
            },
            "$expr": {
                    "$gt": [{
                            "$size": "$prod_size"
                    }, 0]
            }
        }
    }] : 
    [{
        $match: {
            $text: {
                $search: keyword
            },
            "$expr": {
                    "$gt": [{
                            "$size": "$prod_size"
                    }, 0]
            }
        }
    }]
    let stage_query = [
        {
            $sort: {
                "is_favorite": -1,
                "prod_upvotes": -1,
                "prod_sale": -1,
                "score": {
                    $meta: "textScore"
                },
                "prod_updatedtime": -1
            }
        },
        {
            $lookup: {
                from: "discount",
                localField: "prod_site",
                foreignField: "storename",
                as: "dis"
            }
        },
        {
            $project: {
                "dis_price": {
                    $let: {
                        vars: {
                            apply: {
                                $arrayElemAt: ["$dis.apply", 0]
                            },
                            discount_price: {
                                $concat: ["£", {
                                    $toString: [
                                        {
                                            $subtract: [{
                                                $convert: {
                                                    input: {
                                                        $arrayElemAt: [{
                                                            $split: ["$prod_price", "£"]
                                                        }, 1]
                                                    },
                                                    to: "double",
                                                    onError: {
                                                        $toDouble: {
                                                            $concat: [{
                                                                $arrayElemAt: [{
                                                                    $split: [{
                                                                        $arrayElemAt: [{
                                                                            $split: ["$prod_price", "£ "]
                                                                        }, 1]
                                                                    }, ","]
                                                                }, 0]
                                                            }, ".", {
                                                                $arrayElemAt: [{
                                                                    $split: [{
                                                                        $arrayElemAt: [{
                                                                            $split: ["$prod_price", "£ "]
                                                                        }, 1]
                                                                    }, ","]
                                                                }, 1]
                                                            }]
                                                        }
                                                    }
                                                }
                                            }, {
                                                $multiply: [{
                                                    $convert: {
                                                        input: {
                                                            $arrayElemAt: [{
                                                                $split: ["$prod_price", "£"]
                                                            }, 1]
                                                        },
                                                        to: "double",
                                                        onError: {
                                                            $toDouble: {
                                                                $concat: [{
                                                                    $arrayElemAt: [{
                                                                        $split: [{
                                                                            $arrayElemAt: [{
                                                                                $split: ["$prod_price", "£ "]
                                                                            }, 1]
                                                                        }, ","]
                                                                    }, 0]
                                                                }, ".", {
                                                                    $arrayElemAt: [{
                                                                        $split: [{
                                                                            $arrayElemAt: [{
                                                                                $split: ["$prod_price", "£ "]
                                                                            }, 1]
                                                                        }, ","]
                                                                    }, 1]
                                                                }]
                                                            }
                                                        }
                                                    }
                                                }, {
                                                    $divide: [{
                                                        $arrayElemAt: ["$dis.discount_profit", 0]
                                                    }, 100]
                                                }]
                                            }]
                                        }
                                    ]
                                }]
                            }
                        },
                        in: {
                            $switch: {
                                branches: [
                                    {
                                        case: {
                                            $eq: ["$$apply", "full"]
                                        },
                                        then: {
                                            $cond: ["$prod_sale", null, "$$discount_price"]
                                        }
                                    },
                                    {
                                        case: {
                                            $eq: ["$$apply", "sale"]
                                        },
                                        then: {
                                            $cond: ["$prod_sale", "$$discount_price", null]
                                        }
                                    },
                                    {
                                        case: {
                                            $eq: ["$$apply", "both"]
                                        },
                                        then: "$$discount_price"
                                    }
                                ],
                                default: null
                            }
                        }
                    }
                },
                "prod_id": 1,
                "prod_name": 1,
                "prod_url": 1,
                "prod_image": 1,
                "prod_sale": 1,
                "prod_price": 1,
                "prod_oldprice": 1,
                "prod_size": 1,
                "prod_status": 1,
                "prod_site": 1,
                "prod_shortcode": 1,
                "prod_upvotes": 1,
                "is_favorite": 1,
                "is_expired": {
                    $cond: [{
                        $gt: [new Date(), {
                            $arrayElemAt: ["$dis.expireDatetime", 0]
                        }]
                    }, true, false]
                }
            }
        }
    ]
    let query = [...match_query, ...stage_query]
    await ProductModel.aggregate(query)
        .exec((err, products) => {
            if (err) {
                console.error(err)
                return res.status(400).json({ success: false, error: err })
            }
            return res.status(200).json({ success: true, data: products })

        })
}

let updateFavorite = async (req, res) => {
    await ProductModel.findByIdAndUpdate({ _id: req.body.id }, { $set: { "is_favorite": req.body.isf } })
        .exec((error) => {
            if (error) {
                res.status(404).json({ success: false, id: req.body.id })
            }
            res.status(200).json({ success: true, id: req.body.id, status: req.body.isf })
        })
}

let updateVotes = async (req, res) => {
    await ProductModel.findByIdAndUpdate({ _id: req.body.id }, { $inc: { "prod_upvotes": req.body.vote } })
        .exec((error) => {
            if (error) {
                console.log(error)
                res.status(404).json({ success: false, id: req.body.id })
            }
            ProductModel.findOne({ _id: req.body.id }, (err, product) => {
                res.status(200).json({ success: true, id: req.body.id, upvotes: product.prod_upvotes })
            })
        })
}
module.exports = {
    getProducts,
    updateFavorite,
    updateVotes
}