# 0 0   0.3 0   0.4
# 0 0   0.5 0.7 0
# 0 0   0   0   0
# 0 0.2 0.6 0   0
# 1-indexing:
library(Matrix)
i <- c(1, 1, 2, 2, 4, 4)
j <- c(3, 5, 3, 4, 2, 3)
x <- c(0.3, 0.4, 0.5, 0.7, 0.2, 0.6)
rownames <- c("g1", "g2", "g3", "g4")
colnames <- c("c1", "c2", "c3", "c4", "c5")
M <- sparseMatrix(i, j, x=x, dimnames = list(rownames,colnames))
saveRDS(object=M, file="example.RDS")
