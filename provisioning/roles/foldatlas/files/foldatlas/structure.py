# Contains code for analysing RNA structure predictions.

from sklearn import decomposition

data = [
    [ 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1 ],
    [ 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1 ],
    [ 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1 ],
    [ 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1 ],
    [ 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1 ],
    [ 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1 ],
    [ 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1 ],
    [ 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0 ],
    [ 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1 ],
    [ 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1 ]
]


def do_pca( data ):
    # Results are listed in the order that they were added.

    pca = decomposition.PCA( n_components=2 )
    pca.fit( data )
    results = pca.transform( data )

    print( results )


do_pca( data )

# from sklearn import datasets
# iris = datasets.load_iris()
# do_pca(iris.data);
# print(iris.target)
