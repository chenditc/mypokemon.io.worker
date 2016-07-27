sudo docker build -t mypokemon.io.worker .
login_cmd=$(aws ecr get-login)
eval "sudo $login_cmd"
sudo docker tag mypokemon.io.worker:latest 816270155462.dkr.ecr.us-west-2.amazonaws.com/mypokemon.io.worker:latest
sudo docker push 816270155462.dkr.ecr.us-west-2.amazonaws.com/mypokemon.io.worker:latest
eb deploy
